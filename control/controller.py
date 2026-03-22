"""Controller orchestrator: normalize -> route -> review -> policy.

Returns (ControllerDecision, ReviewEpisode | None) per the handoff contract.
Event logging is done by the runtime, not here.
"""

import logging as _stdlib_logging
import json
import time

from control.action_normalizer import normalize
import math
from control.a11y_parser import parse_tree, match_target, NEAREST_RADIUS
from control.critical_router import route
from control.reviewer import (
    generate_legibility,
    review as reviewer_review,
    trusted_fallback_action as reviewer_trusted_fallback,
)
from control.types import (
    no_target_match,
    controller_decision,
    review_episode,
    MODE_ALLOWED_DECISIONS,
)

_logger = _stdlib_logging.getLogger("desktopenv.control")

# For linearizing a11y tree in review packages
try:
    from mm_agents.agent import linearize_accessibility_tree as _linearize_tree
except ImportError:
    def _linearize_tree(raw):
        return str(raw) if raw else ""


# ---- module-level logger ----
# Set by lib_run_single.py before the action loop via set_logger().
_current_logger = None


def set_logger(logger):
    """Set the control logger for the current run. Call before review()."""
    global _current_logger
    _current_logger = logger


def _nearby_text(nodes: list[dict], x: float, y: float, target_fields: dict) -> str:
    """Collect name/text from a11y nodes near (x, y) excluding the matched target."""
    parts = []
    target_bounds = target_fields.get("target_bounds") or {}
    for node in nodes:
        # Skip the matched target node (exact bounds match)
        if (node["x"] == target_bounds.get("x")
                and node["y"] == target_bounds.get("y")
                and node["w"] == target_bounds.get("w")
                and node["h"] == target_bounds.get("h")):
            continue
        cx = node["x"] + node["w"] / 2
        cy = node["y"] + node["h"] / 2
        if math.hypot(x - cx, y - cy) <= NEAREST_RADIUS:
            if node["name"]:
                parts.append(node["name"])
            if node["text"]:
                parts.append(node["text"])
    return " ".join(parts)


def review(
    instruction: str,
    obs: dict,
    raw_response: str,
    raw_action: str,
    recent_history: list[dict],
    step_idx: int,
    task_id: str,
    domain: str,
    config: dict,
    action_source_hint: str = "untrusted",
) -> tuple[dict, dict | None]:
    """Orchestrate the control protocol for one action.

    Returns (ControllerDecision, ReviewEpisode | None).
    ReviewEpisode is None when the action was not reviewed.
    """
    # 0. Fast path: control disabled
    if not config.get("enabled", False):
        return (
            controller_decision(
                execute=True, was_critical=False,
                action_to_execute=raw_action, action_source=action_source_hint,
            ),
            None,
        )

    # 1. Normalize action
    try:
        normalized = normalize(raw_action)
    except Exception as e:
        _logger.error(json.dumps({
            "event": "action_parse_error",
            "task_id": task_id,
            "step": step_idx,
            "error": str(e),
        }))
        return (
            controller_decision(
                execute=False, was_critical=False,
                termination_reason="unparsable_action",
            ),
            None,
        )

    # 2. Parse a11y and match target (click-like actions with coordinates only)
    a11y_raw = obs.get("accessibility_tree", "")
    a11y_linearized = ""
    if a11y_raw:
        try:
            a11y_linearized = _linearize_tree(a11y_raw)
        except Exception as e:
            _logger.warning(json.dumps({
                "event": "a11y_linearize_error",
                "task_id": task_id,
                "step": step_idx,
                "error": str(e),
            }))

    if a11y_linearized and normalized.get("x") is not None:
        try:
            nodes = parse_tree(a11y_linearized)
            target_fields = match_target(nodes, normalized["x"], normalized["y"])
            normalized.update(target_fields)
            # Collect text from nearby a11y nodes for keyword matching
            normalized["nearby_text"] = _nearby_text(
                nodes, normalized["x"], normalized["y"], target_fields,
            )
        except Exception as e:
            _logger.warning(json.dumps({
                "event": "a11y_parse_error",
                "task_id": task_id,
                "step": step_idx,
                "error": str(e),
            }))
            normalized.update(no_target_match())

    # Ensure target_* fields exist even when a11y was skipped
    if "target_matched" not in normalized:
        normalized.update(no_target_match())

    # 3. Route (inject domain for context-aware routing)
    config["_domain"] = domain
    router_dec = route(normalized, config)
    config.pop("_domain", None)

    is_critical = router_dec["critical"]

    # 4. If not critical, allow immediately (no episode)
    if not is_critical:
        return (
            controller_decision(
                execute=True, was_critical=False,
                action_to_execute=raw_action, action_source=action_source_hint,
            ),
            None,
        )

    # 5. Legibility (critical only, optional)
    legibility_report = None
    if config.get("legibility_enabled"):
        try:
            legibility_report = generate_legibility(
                instruction, obs, raw_response, normalized, recent_history, config
            )
        except Exception as e:
            _logger.warning(json.dumps({
                "event": "legibility_error",
                "task_id": task_id,
                "step": step_idx,
                "error": str(e),
            }))

    # 6. Build review package
    mode = config.get("controller_mode", "allow_or_terminate")
    package = {
        "instruction": instruction,
        "raw_response": raw_response,
        "raw_action": raw_action,
        "normalized_action": normalized,
        "router_decision": router_dec,
        "obs": obs,
        "a11y_tree_linearized": a11y_linearized,
        "legibility_report": legibility_report,
        "recent_history": recent_history,
        "step_index": step_idx,
        "task_id": task_id,
        "domain": domain,
        "controller_mode": mode,
        "action_source": action_source_hint,
    }

    # 7. Save review package
    review_package_path = None
    if _current_logger:
        review_package_path = _current_logger.save_review_package(package, step_idx)

    # 8. Trusted review
    reviewer_result = None
    review_latency_ms = None
    reviewer_model = config.get("reviewer_model", "gpt-5.4-mini")

    try:
        t0 = time.time()
        reviewer_result = reviewer_review(package, config)
        review_latency_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        _logger.error(json.dumps({
            "event": "review_error",
            "task_id": task_id,
            "step": step_idx,
            "error": str(e),
        }))
        if config.get("fail_closed_on_review_error", True):
            episode = review_episode(
                task_id=task_id, domain=domain, step_index=step_idx,
                raw_action=raw_action, normalized_action=normalized,
                router_decision=router_dec, action_source=action_source_hint,
                legibility_report=legibility_report, reviewer_result=None,
                review_latency_ms=None, reviewer_model=reviewer_model,
                review_package_path=review_package_path,
            )
            return (
                controller_decision(
                    execute=False, was_critical=True,
                    termination_reason="review_error_fail_closed",
                ),
                episode,
            )
        raise

    # 9. Build episode (always for critical actions)
    episode = review_episode(
        task_id=task_id, domain=domain, step_index=step_idx,
        raw_action=raw_action, normalized_action=normalized,
        router_decision=router_dec, action_source=action_source_hint,
        legibility_report=legibility_report, reviewer_result=reviewer_result,
        review_latency_ms=review_latency_ms, reviewer_model=reviewer_model,
        review_package_path=review_package_path,
    )

    # 10. Apply policy based on reviewer decision and controller mode
    decision_str = reviewer_result["decision"]

    # Clamp decisions not valid for this mode
    allowed = MODE_ALLOWED_DECISIONS.get(mode, {"ALLOW", "BLOCK"})
    if decision_str not in allowed:
        _logger.warning(json.dumps({
            "event": "decision_clamped_to_block",
            "task_id": task_id,
            "step": step_idx,
            "original_decision": decision_str,
            "mode": mode,
        }))
        decision_str = "BLOCK"

    if decision_str == "ALLOW":
        return (
            controller_decision(
                execute=True, was_critical=True,
                reviewer_decision="ALLOW",
                action_to_execute=raw_action,
                action_source=action_source_hint,
            ),
            episode,
        )

    if decision_str == "BLOCK":
        return (
            controller_decision(
                execute=False, was_critical=True,
                reviewer_decision="BLOCK",
                termination_reason=reviewer_result.get("primary_reason", "blocked_by_reviewer"),
            ),
            episode,
        )

    if decision_str == "RESAMPLE":
        # Only valid in allow_or_resample_once -- signal runtime to resample
        return (
            controller_decision(
                execute=False, was_critical=True,
                reviewer_decision="RESAMPLE",
                resample_requested=True,
            ),
            episode,
        )

    if decision_str == "DEFER_TO_TRUSTED":
        # Only valid in allow_or_trusted_fallback_once -- generate fallback here
        return _handle_trusted_fallback(
            package, reviewer_result, config, episode,
            task_id, step_idx,
        )

    # Should not reach here, but fail closed
    return (
        controller_decision(
            execute=False, was_critical=True,
            termination_reason=f"unknown_reviewer_decision_{decision_str}",
        ),
        episode,
    )


def _handle_trusted_fallback(
    package: dict,
    reviewer_result: dict,
    config: dict,
    episode: dict,
    task_id: str,
    step_idx: int,
) -> tuple[dict, dict]:
    """Handle DEFER_TO_TRUSTED by generating one trusted fallback action."""
    try:
        fallback_result = reviewer_trusted_fallback(package, reviewer_result, config)
    except Exception as e:
        _logger.error(json.dumps({
            "event": "trusted_fallback_error",
            "task_id": task_id,
            "step": step_idx,
            "error": str(e),
        }))
        episode["trusted_fallback_result"] = {
            "action": None, "reason": f"trusted_fallback_error: {e}", "confidence": 0.0,
        }
        return (
            controller_decision(
                execute=False, was_critical=True,
                reviewer_decision="DEFER_TO_TRUSTED",
                termination_reason="trusted_fallback_error",
                trusted_fallback_requested=True,
            ),
            episode,
        )

    fallback_action = fallback_result.get("action")

    # Validate fallback action is non-empty
    if not fallback_action or not fallback_action.strip():
        _logger.warning(json.dumps({
            "event": "trusted_fallback_empty",
            "task_id": task_id,
            "step": step_idx,
        }))
        episode["trusted_fallback_result"] = fallback_result
        return (
            controller_decision(
                execute=False, was_critical=True,
                reviewer_decision="DEFER_TO_TRUSTED",
                termination_reason="trusted_fallback_empty",
                trusted_fallback_requested=True,
            ),
            episode,
        )

    # Validate fallback action parses
    try:
        normalize(fallback_action)
    except Exception as e:
        _logger.warning(json.dumps({
            "event": "trusted_fallback_unparsable",
            "task_id": task_id,
            "step": step_idx,
            "error": str(e),
        }))
        episode["trusted_fallback_result"] = fallback_result
        return (
            controller_decision(
                execute=False, was_critical=True,
                reviewer_decision="DEFER_TO_TRUSTED",
                termination_reason="trusted_fallback_unparsable",
                trusted_fallback_requested=True,
            ),
            episode,
        )

    # Valid fallback -- execute it (not re-reviewed in this implementation)
    episode["trusted_fallback_result"] = fallback_result
    return (
        controller_decision(
            execute=True, was_critical=True,
            reviewer_decision="DEFER_TO_TRUSTED",
            action_to_execute=fallback_action,
            action_source="trusted_fallback",
            trusted_fallback_requested=True,
        ),
        episode,
    )
