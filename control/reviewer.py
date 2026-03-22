"""Trusted reviewer, legibility generation, and trusted fallback action.

generate_legibility() -- calls untrusted model, never raises, returns None on error.
review() -- calls trusted model, raises on error (controller fails closed).
trusted_fallback_action() -- calls trusted model, raises on error (runtime terminates).
"""

import base64
import json
import logging
import os
import re

import requests

# For linearizing a11y tree from obs
try:
    from mm_agents.agent import linearize_accessibility_tree as _linearize_tree
except ImportError:
    def _linearize_tree(raw):
        return str(raw) if raw else ""

from control.prompts import (
    LEGIBILITY_PROMPT,
    TRUSTED_FALLBACK_PROMPT,
    build_visual_context,
    format_action_summary,
    format_history,
    get_reviewer_prompt,
)
from control.types import MODE_ALLOWED_DECISIONS, VALID_DECISIONS

logger = logging.getLogger(__name__)


# ---- public API ----

def generate_legibility(instruction: str, obs: dict, raw_response: str,
                        action: dict, recent_history: list[dict],
                        config: dict) -> dict | None:
    """Generate a legibility report for a critical action.

    Calls the untrusted agent model to explain the action.
    Never raises -- returns None on any error.
    """
    try:
        a11y_raw = obs.get("accessibility_tree", "")
        a11y_linearized = _linearize_tree(a11y_raw) if a11y_raw else ""

        prompt_text = LEGIBILITY_PROMPT.format(
            instruction=instruction,
            raw_response=raw_response[:2000],
            action_summary=format_action_summary(action),
            recent_history=format_history(recent_history),
            a11y_context=a11y_linearized[:3000],
        )

        model = config.get("legibility_model", "gpt-4o-mini")
        messages = _build_messages(prompt_text, obs, include_screenshot=True)
        response_text = _call_llm(model, messages)
        return _validate_legibility(_parse_json_response(response_text))

    except Exception:
        logger.exception(json.dumps({"event": "legibility_generation_failed"}))
        return None


def _run_review(prompt_text: str, obs: dict, include_screenshot: bool,
                model: str, controller_mode: str) -> dict:
    """Shared review call: format messages, call LLM, parse, validate.

    Used by review() for runtime and by ablation for offline re-runs.
    """
    messages = _build_messages(prompt_text, obs,
                               include_screenshot=include_screenshot)
    response_text = _call_llm(model, messages,
                              response_format={"type": "json_object"})
    logger.debug("reviewer raw response: %s", response_text[:500])

    allowed = MODE_ALLOWED_DECISIONS.get(controller_mode)
    return _validate_reviewer_result(_parse_json_response(response_text),
                                     allowed_decisions=allowed)


def review(package: dict, config: dict) -> dict:
    """Review a critical action. Returns ReviewerResult dict with 4-way decision.

    Raises on any error -- the controller catches and fails closed.
    """
    instruction = package["instruction"]
    raw_response = package["raw_response"]
    action = package["normalized_action"]
    recent_history = package.get("recent_history", [])
    obs = package.get("obs", {})
    controller_mode = package.get("controller_mode", "allow_or_terminate")

    # Build visual context conditionally
    visual_context = ""
    include_visual = config.get("include_visual_context", False)
    if include_visual:
        a11y_tree = package.get("a11y_tree_linearized", "")
        legibility_report = package.get("legibility_report")
        visual_context = build_visual_context(a11y_tree, legibility_report)

    # Select mode-aware prompt
    prompt_template = get_reviewer_prompt(controller_mode)
    prompt_text = prompt_template.format(
        instruction=instruction,
        raw_response=raw_response[:2000],
        action_summary=format_action_summary(action),
        recent_history=format_history(recent_history),
        visual_context=visual_context,
    )

    model = config.get("reviewer_model", "gpt-5.4-mini")
    include_screenshot = include_visual and obs.get("screenshot")
    return _run_review(prompt_text, obs, bool(include_screenshot),
                       model, controller_mode)


def trusted_fallback_action(package: dict, reviewer_result: dict,
                            config: dict) -> dict:
    """Generate a single trusted fallback action.

    Called only when the reviewer chose DEFER_TO_TRUSTED.
    Raises on error -- runtime terminates if fallback is unusable.
    """
    instruction = package["instruction"]
    action = package["normalized_action"]
    recent_history = package.get("recent_history", [])
    obs = package.get("obs", {})

    # Build visual context
    visual_context = ""
    include_visual = config.get("include_visual_context", False)
    if include_visual:
        a11y_tree = package.get("a11y_tree_linearized", "")
        legibility_report = package.get("legibility_report")
        visual_context = build_visual_context(a11y_tree, legibility_report)

    prompt_text = TRUSTED_FALLBACK_PROMPT.format(
        instruction=instruction,
        rejected_action=package.get("raw_action", "")[:2000],
        reviewer_decision=reviewer_result.get("decision", "DEFER_TO_TRUSTED"),
        reviewer_reason=reviewer_result.get("primary_reason", ""),
        reviewer_evidence=json.dumps(reviewer_result.get("evidence", [])),
        action_summary=format_action_summary(action),
        recent_history=format_history(recent_history),
        visual_context=visual_context,
    )

    model = config.get("trusted_fallback_model",
                       config.get("reviewer_model", "gpt-5.4-mini"))
    include_screenshot = include_visual and obs.get("screenshot")
    messages = _build_messages(prompt_text, obs,
                               include_screenshot=bool(include_screenshot))

    response_text = _call_llm(model, messages,
                              response_format={"type": "json_object"})
    logger.debug("trusted_fallback raw response: %s", response_text[:500])
    return _validate_trusted_fallback(_parse_json_response(response_text))


# ---- internal helpers ----

def _build_messages(prompt_text: str, obs: dict,
                    include_screenshot: bool = False) -> list[dict]:
    """Build the messages list for the LLM call."""
    content = [{"type": "text", "text": prompt_text}]

    if include_screenshot and obs.get("screenshot"):
        screenshot_b64 = base64.b64encode(obs["screenshot"]).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{screenshot_b64}",
            },
        })

    return [{"role": "user", "content": content}]


def _call_llm(model: str, messages: list[dict],
              response_format: dict | None = None) -> str:
    """Call an LLM via OpenAI or Anthropic API.

    Routes by model name prefix. Uses requests.post() directly,
    matching the pattern in mm_agents/agent.py.
    """
    if model.startswith("gpt") or model.startswith("o"):
        return _call_openai(model, messages, response_format=response_format)
    elif model.startswith("claude"):
        return _call_anthropic(model, messages)
    else:
        raise ValueError(f"Unsupported model prefix: {model}")


def _call_openai(model: str, messages: list[dict],
                 response_format: dict | None = None) -> str:
    """Call OpenAI chat completions API."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
    }

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
    }

    # Newer models (gpt-5.x, o-series) use max_completion_tokens
    if model.startswith("o") or model.startswith("gpt-5"):
        payload.pop("temperature", None)
        payload["max_completion_tokens"] = 1500
    else:
        payload["max_tokens"] = 1500

    if response_format is not None:
        payload["response_format"] = response_format

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenAI API error {response.status_code}: {response.text[:500]}"
        )

    return response.json()["choices"][0]["message"]["content"]


def _call_anthropic(model: str, messages: list[dict]) -> str:
    """Call Anthropic messages API."""
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Convert to Anthropic message format
    claude_messages = []
    for msg in messages:
        claude_content = []
        for part in msg["content"]:
            if part["type"] == "text":
                claude_content.append({"type": "text", "text": part["text"]})
            elif part["type"] == "image_url":
                url = part["image_url"]["url"]
                b64_data = url.replace("data:image/png;base64,", "")
                claude_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64_data,
                    },
                })
        claude_messages.append({"role": msg["role"], "content": claude_content})

    payload = {
        "model": model,
        "max_tokens": 1500,
        "messages": claude_messages,
        "temperature": 0.1,
    }

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error {response.status_code}: {response.text[:500]}"
        )

    return response.json()["content"][0]["text"]


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response: {text[:300]}")


# ---- schema validation ----

_REVIEWER_REQUIRED = {"decision", "risk_score", "primary_reason", "evidence",
                      "safer_alternative"}

_LEGIBILITY_FIELDS = {
    "action_type", "target_element", "target_text_or_label",
    "why_needed_for_user_goal", "expected_visible_effect_next",
    "what_could_go_wrong", "security_relevance", "confidence",
}

_MULTI_ACTION_RE = re.compile(r"pyautogui\.\w+\(", re.IGNORECASE)


def _validate_reviewer_result(parsed: dict,
                              allowed_decisions: set[str] | None = None) -> dict:
    """Validate ReviewerResult schema. Raises on missing or mis-typed fields."""
    missing = _REVIEWER_REQUIRED - set(parsed.keys())
    if missing:
        raise ValueError(f"Reviewer response missing required fields: {missing}")

    # decision must be a valid enum value
    decision = parsed["decision"]
    if decision not in VALID_DECISIONS:
        raise ValueError(
            f"Reviewer 'decision' must be one of {VALID_DECISIONS}, got: {decision!r}"
        )

    # If mode-specific allowed set is given, enforce it
    if allowed_decisions and decision not in allowed_decisions:
        raise ValueError(
            f"Reviewer decision {decision!r} not allowed in current mode. "
            f"Allowed: {allowed_decisions}"
        )

    # risk_score must be numeric
    if not isinstance(parsed["risk_score"], (int, float)):
        raise ValueError(
            f"Reviewer 'risk_score' must be numeric, got {type(parsed['risk_score']).__name__}"
        )

    # evidence must be a list
    if not isinstance(parsed["evidence"], list):
        raise ValueError(
            f"Reviewer 'evidence' must be a list, got {type(parsed['evidence']).__name__}"
        )

    return parsed


def _validate_trusted_fallback(parsed: dict) -> dict:
    """Validate TrustedFallbackResult schema. Raises on malformed output."""
    for field in ("action", "reason", "confidence"):
        if field not in parsed:
            raise ValueError(f"Trusted fallback missing required field: {field}")

    action = parsed["action"]
    if action is not None and not isinstance(action, str):
        raise ValueError(
            f"Trusted fallback 'action' must be str or null, "
            f"got {type(action).__name__}"
        )

    # Reject multi-action text
    if isinstance(action, str):
        matches = _MULTI_ACTION_RE.findall(action)
        if len(matches) > 1:
            raise ValueError(
                f"Trusted fallback produced multiple actions ({len(matches)} "
                f"pyautogui calls found). Must be exactly one."
            )

    if not isinstance(parsed["confidence"], (int, float)):
        raise ValueError(
            f"Trusted fallback 'confidence' must be numeric, "
            f"got {type(parsed['confidence']).__name__}"
        )

    return parsed


def _validate_legibility(parsed: dict) -> dict:
    """Validate LegibilityReport schema. Fills None for missing fields (graceful)."""
    for field in _LEGIBILITY_FIELDS:
        parsed.setdefault(field, None)
    return parsed
