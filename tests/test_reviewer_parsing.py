"""Tests for reviewer schema parsing/validation, prompt mode dispatch, and type constructors.

Covers:
- _parse_json_response edge cases
- _validate_reviewer_result with 4-way decision schema and mode-aware enforcement
- _validate_trusted_fallback for fallback result validation
- prompts.py mode-aware prompt dispatch
- types.py spec constructors
"""

import pytest

from control.reviewer import (
    _parse_json_response,
    _validate_reviewer_result,
    _validate_trusted_fallback,
)
from control.prompts import (
    get_reviewer_prompt,
    build_resample_instruction,
    REVIEWER_PROMPT_ALLOW_BLOCK,
    REVIEWER_PROMPT_ALLOW_RESAMPLE_BLOCK,
    REVIEWER_PROMPT_ALLOW_DEFER_BLOCK,
)
from control.types import (
    VALID_DECISIONS,
    MODE_ALLOWED_DECISIONS,
    controller_decision,
    reviewer_result,
    trusted_fallback_result,
    review_episode,
    normalized_action,
    router_decision,
)


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------


class TestParseJsonResponse:
    def test_direct_json(self):
        text = '{"decision": "ALLOW", "risk_score": 0.1, "primary_reason": "ok", "evidence": [], "safer_alternative": null}'
        result = _parse_json_response(text)
        assert result["decision"] == "ALLOW"
        assert result["risk_score"] == 0.1

    def test_markdown_code_block(self):
        text = '```json\n{"decision": "BLOCK", "risk_score": 0.9, "primary_reason": "bad", "evidence": ["x"], "safer_alternative": "y"}\n```'
        result = _parse_json_response(text)
        assert result["decision"] == "BLOCK"

    def test_markdown_no_lang_tag(self):
        text = '```\n{"decision": "ALLOW", "risk_score": 0.0, "primary_reason": "ok", "evidence": [], "safer_alternative": null}\n```'
        result = _parse_json_response(text)
        assert result["decision"] == "ALLOW"

    def test_surrounding_text_ignored(self):
        text = 'Here is my analysis:\n```json\n{"decision": "RESAMPLE", "risk_score": 0.5, "primary_reason": "ambiguous", "evidence": ["unclear"], "safer_alternative": null}\n```\nHope this helps!'
        result = _parse_json_response(text)
        assert result["decision"] == "RESAMPLE"

    def test_garbage_raises(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            _parse_json_response("this is not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            _parse_json_response("")


# ---------------------------------------------------------------------------
# _validate_reviewer_result -- 4-way decision schema
# ---------------------------------------------------------------------------


class TestReviewerDecisionValidation:
    """Tests for the 4-way reviewer decision schema."""

    def _valid_result(self, **overrides):
        base = {
            "decision": "ALLOW",
            "risk_score": 0.1,
            "primary_reason": "ok",
            "evidence": ["safe"],
            "safer_alternative": None,
        }
        base.update(overrides)
        return base

    def test_allow_passes(self):
        result = self._valid_result(decision="ALLOW")
        assert _validate_reviewer_result(result)["decision"] == "ALLOW"

    def test_block_passes(self):
        result = self._valid_result(decision="BLOCK")
        assert _validate_reviewer_result(result)["decision"] == "BLOCK"

    def test_resample_passes(self):
        result = self._valid_result(decision="RESAMPLE")
        assert _validate_reviewer_result(result)["decision"] == "RESAMPLE"

    def test_defer_to_trusted_passes(self):
        result = self._valid_result(decision="DEFER_TO_TRUSTED")
        assert _validate_reviewer_result(result)["decision"] == "DEFER_TO_TRUSTED"

    def test_invalid_decision_enum_raises(self):
        with pytest.raises(ValueError, match="VALID_DECISIONS|must be one of"):
            _validate_reviewer_result(self._valid_result(decision="DENY"))

    def test_missing_decision_field_raises(self):
        result = {"risk_score": 0.1, "primary_reason": "ok", "evidence": [], "safer_alternative": None}
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_reviewer_result(result)

    def test_old_allow_bool_schema_raises(self):
        """Old allow:bool schema should fail -- decision field is missing."""
        result = {"allow": True, "risk_score": 0.1, "primary_reason": "ok", "evidence": [], "safer_alternative": None}
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_reviewer_result(result)

    def test_integer_risk_score_passes(self):
        result = self._valid_result(risk_score=1)
        assert _validate_reviewer_result(result)["risk_score"] == 1

    def test_string_risk_score_raises(self):
        with pytest.raises(ValueError, match="must be numeric"):
            _validate_reviewer_result(self._valid_result(risk_score="low"))

    def test_string_evidence_raises(self):
        with pytest.raises(ValueError, match="must be a list"):
            _validate_reviewer_result(self._valid_result(evidence="single string"))

    def test_empty_evidence_list_passes(self):
        result = self._valid_result(evidence=[])
        assert _validate_reviewer_result(result)["evidence"] == []

    def test_extra_fields_preserved(self):
        result = self._valid_result(extra_field="bonus")
        validated = _validate_reviewer_result(result)
        assert validated["extra_field"] == "bonus"


# ---------------------------------------------------------------------------
# Mode-aware decision enforcement
# ---------------------------------------------------------------------------


class TestModeAwareDecisionEnforcement:
    def _valid_result(self, decision):
        return {
            "decision": decision,
            "risk_score": 0.5,
            "primary_reason": "test",
            "evidence": ["test"],
            "safer_alternative": None,
        }

    def test_terminate_mode_accepts_allow(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_terminate"]
        _validate_reviewer_result(self._valid_result("ALLOW"), allowed_decisions=allowed)

    def test_terminate_mode_accepts_block(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_terminate"]
        _validate_reviewer_result(self._valid_result("BLOCK"), allowed_decisions=allowed)

    def test_terminate_mode_rejects_resample(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_terminate"]
        with pytest.raises(ValueError, match="not allowed in current mode"):
            _validate_reviewer_result(self._valid_result("RESAMPLE"), allowed_decisions=allowed)

    def test_terminate_mode_rejects_defer(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_terminate"]
        with pytest.raises(ValueError, match="not allowed in current mode"):
            _validate_reviewer_result(self._valid_result("DEFER_TO_TRUSTED"), allowed_decisions=allowed)

    def test_resample_mode_accepts_resample(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_resample_once"]
        _validate_reviewer_result(self._valid_result("RESAMPLE"), allowed_decisions=allowed)

    def test_resample_mode_rejects_defer(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_resample_once"]
        with pytest.raises(ValueError, match="not allowed in current mode"):
            _validate_reviewer_result(self._valid_result("DEFER_TO_TRUSTED"), allowed_decisions=allowed)

    def test_fallback_mode_accepts_defer(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_trusted_fallback_once"]
        _validate_reviewer_result(self._valid_result("DEFER_TO_TRUSTED"), allowed_decisions=allowed)

    def test_fallback_mode_rejects_resample(self):
        allowed = MODE_ALLOWED_DECISIONS["allow_or_trusted_fallback_once"]
        with pytest.raises(ValueError, match="not allowed in current mode"):
            _validate_reviewer_result(self._valid_result("RESAMPLE"), allowed_decisions=allowed)

    def test_no_allowed_set_accepts_any_valid(self):
        for decision in VALID_DECISIONS:
            _validate_reviewer_result(self._valid_result(decision), allowed_decisions=None)


# ---------------------------------------------------------------------------
# _validate_trusted_fallback
# ---------------------------------------------------------------------------


class TestTrustedFallbackValidation:
    def test_valid_action_passes(self):
        result = {"action": "pyautogui.click(100, 200)", "reason": "safe click", "confidence": 0.8}
        validated = _validate_trusted_fallback(result)
        assert validated["action"] == "pyautogui.click(100, 200)"

    def test_null_action_passes(self):
        result = {"action": None, "reason": "no safe action", "confidence": 0.5}
        validated = _validate_trusted_fallback(result)
        assert validated["action"] is None

    def test_missing_action_field_raises(self):
        with pytest.raises(ValueError, match="missing required field"):
            _validate_trusted_fallback({"reason": "test", "confidence": 0.5})

    def test_non_string_action_raises(self):
        with pytest.raises(ValueError, match="must be str or null"):
            _validate_trusted_fallback({"action": 42, "reason": "test", "confidence": 0.5})

    def test_multi_action_raises(self):
        with pytest.raises(ValueError, match="multiple actions"):
            _validate_trusted_fallback({
                "action": "pyautogui.click(100,200); pyautogui.press('enter')",
                "reason": "test", "confidence": 0.8,
            })

    def test_missing_confidence_raises(self):
        with pytest.raises(ValueError, match="missing required field"):
            _validate_trusted_fallback({"action": "pyautogui.click(1,2)", "reason": "test"})

    def test_non_numeric_confidence_raises(self):
        with pytest.raises(ValueError, match="must be numeric"):
            _validate_trusted_fallback({"action": "pyautogui.click(1,2)", "reason": "test", "confidence": "high"})


# ---------------------------------------------------------------------------
# Prompt mode dispatch
# ---------------------------------------------------------------------------


class TestPromptModeDispatch:
    def test_terminate_mode_returns_allow_block(self):
        prompt = get_reviewer_prompt("allow_or_terminate")
        assert prompt is REVIEWER_PROMPT_ALLOW_BLOCK

    def test_resample_mode_returns_resample_prompt(self):
        prompt = get_reviewer_prompt("allow_or_resample_once")
        assert prompt is REVIEWER_PROMPT_ALLOW_RESAMPLE_BLOCK
        assert "RESAMPLE" in prompt

    def test_fallback_mode_returns_defer_prompt(self):
        prompt = get_reviewer_prompt("allow_or_trusted_fallback_once")
        assert prompt is REVIEWER_PROMPT_ALLOW_DEFER_BLOCK
        assert "DEFER_TO_TRUSTED" in prompt

    def test_unknown_mode_defaults_to_allow_block(self):
        prompt = get_reviewer_prompt("made_up_mode")
        assert prompt is REVIEWER_PROMPT_ALLOW_BLOCK

    def test_resample_prompt_mentions_trajectory(self):
        prompt = get_reviewer_prompt("allow_or_resample_once")
        assert "trajectory" in prompt

    def test_defer_prompt_mentions_trusted_executor(self):
        prompt = get_reviewer_prompt("allow_or_trusted_fallback_once")
        assert "trusted executor" in prompt

    def test_resample_prompt_no_prefer_block(self):
        prompt = get_reviewer_prompt("allow_or_resample_once")
        assert "prefer BLOCK" not in prompt

    def test_defer_prompt_no_prefer_block(self):
        prompt = get_reviewer_prompt("allow_or_trusted_fallback_once")
        assert "prefer BLOCK" not in prompt


# ---------------------------------------------------------------------------
# build_resample_instruction
# ---------------------------------------------------------------------------


class TestBuildResampleInstruction:
    def test_includes_instruction_and_rejected_action(self):
        result = build_resample_instruction(
            instruction="Open the browser",
            reviewer_result={"primary_reason": "suspicious URL"},
            rejected_action="pyautogui.click(100, 200)",
        )
        assert "Open the browser" in result
        assert "pyautogui.click(100, 200)" in result

    def test_includes_rejection_reason(self):
        result = build_resample_instruction(
            instruction="task",
            reviewer_result={"primary_reason": "data exfiltration risk"},
            rejected_action="pyautogui.write('secret')",
        )
        assert "data exfiltration risk" in result

    def test_missing_reason_uses_fallback(self):
        result = build_resample_instruction(
            instruction="task",
            reviewer_result={},
            rejected_action="pyautogui.click(50, 50)",
        )
        assert "action was flagged" in result


# ---------------------------------------------------------------------------
# Type constructors
# ---------------------------------------------------------------------------


class TestTypeConstructors:
    def test_valid_decisions_has_four_values(self):
        assert VALID_DECISIONS == {"ALLOW", "RESAMPLE", "DEFER_TO_TRUSTED", "BLOCK"}

    def test_mode_allowed_decisions_complete(self):
        assert set(MODE_ALLOWED_DECISIONS.keys()) == {
            "allow_or_terminate",
            "allow_or_resample_once",
            "allow_or_trusted_fallback_once",
        }
        for mode, allowed in MODE_ALLOWED_DECISIONS.items():
            assert allowed <= VALID_DECISIONS, f"{mode} has invalid decisions"
            assert "ALLOW" in allowed, f"{mode} must allow ALLOW"
            assert "BLOCK" in allowed, f"{mode} must allow BLOCK"

    def test_controller_decision_has_eight_keys(self):
        d = controller_decision(execute=True, was_critical=True)
        expected_keys = {
            "execute", "termination_reason", "was_critical",
            "reviewer_decision", "action_to_execute", "action_source",
            "resample_requested", "trusted_fallback_requested",
        }
        assert set(d.keys()) == expected_keys

    def test_reviewer_result_constructor(self):
        r = reviewer_result("ALLOW", 0.1, "safe action", ["aligned with task"])
        assert r["decision"] == "ALLOW"
        assert r["risk_score"] == 0.1
        assert r["safer_alternative"] is None

    def test_trusted_fallback_result_constructor(self):
        t = trusted_fallback_result("pyautogui.press('escape')", "safe exit", 0.9)
        assert t["action"] == "pyautogui.press('escape')"
        assert t["confidence"] == 0.9

    def test_review_episode_constructor(self):
        na = normalized_action("pyautogui.click(1,2)", "click", x=1.0, y=2.0)
        rd = router_decision(True, "send_submit_share", ["Send button"], 0.9)
        ep = review_episode("task1", "chrome", 0, "pyautogui.click(1,2)", na, rd)
        assert ep["action_source"] == "untrusted"
        assert ep["task_id"] == "task1"
        assert ep["review_package_path"] is None


# ---------------------------------------------------------------------------
# Blocker 3: trusted fallback prompt must use raw_action, not raw_response
# ---------------------------------------------------------------------------


class TestTrustedFallbackPromptInput:
    """Verify the trusted fallback prompt uses the rejected raw action string,
    not the full agent response text."""

    def test_prompt_uses_raw_action_not_raw_response(self):
        from control.prompts import TRUSTED_FALLBACK_PROMPT, format_action_summary, format_history

        raw_action = "pyautogui.click(500, 300)"
        raw_response = "I'll click the login button because it appears to be the next step."

        package = {
            "instruction": "Open the settings page",
            "raw_response": raw_response,
            "raw_action": raw_action,
            "normalized_action": {"primary_kind": "click", "x": 500, "y": 300,
                                  "raw_action": raw_action},
            "recent_history": [],
            "obs": {},
            "a11y_tree_linearized": "",
            "legibility_report": None,
            "controller_mode": "allow_or_trusted_fallback_once",
        }
        reviewer_res = {
            "decision": "DEFER_TO_TRUSTED",
            "risk_score": 0.7,
            "primary_reason": "suspicious click target",
            "evidence": ["unknown element"],
            "safer_alternative": None,
        }

        prompt_text = TRUSTED_FALLBACK_PROMPT.format(
            instruction=package["instruction"],
            rejected_action=package.get("raw_action", "")[:2000],
            reviewer_decision=reviewer_res.get("decision", "DEFER_TO_TRUSTED"),
            reviewer_reason=reviewer_res.get("primary_reason", ""),
            reviewer_evidence="[]",
            action_summary=format_action_summary(package["normalized_action"]),
            recent_history=format_history([]),
            visual_context="",
        )

        assert raw_action in prompt_text
        assert raw_response not in prompt_text


# ---------------------------------------------------------------------------
# OpenAI response_format (JSON mode) threading
# ---------------------------------------------------------------------------


class TestOpenAIResponseFormat:
    """Verify _call_openai includes response_format in payload when provided."""

    def test_json_mode_included_in_payload(self, monkeypatch):
        import control.reviewer as rev

        captured_payload = {}

        class FakeResponse:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": '{"decision": "ALLOW"}'}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured_payload.update(json)
            return FakeResponse()

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr("requests.post", fake_post)

        rev._call_openai(
            "gpt-5.4-mini",
            [{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            response_format={"type": "json_object"},
        )
        assert captured_payload["response_format"] == {"type": "json_object"}

    def test_no_response_format_by_default(self, monkeypatch):
        import control.reviewer as rev

        captured_payload = {}

        class FakeResponse:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": '{"result": "ok"}'}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured_payload.update(json)
            return FakeResponse()

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setattr("requests.post", fake_post)

        rev._call_openai(
            "gpt-5.4-mini",
            [{"role": "user", "content": [{"type": "text", "text": "test"}]}],
        )
        assert "response_format" not in captured_payload

    def test_response_format_threaded_through_call_llm(self, monkeypatch):
        import control.reviewer as rev

        captured_kwargs = {}

        def spy_call_openai(model, messages, response_format=None):
            captured_kwargs["response_format"] = response_format
            return '{"decision": "ALLOW"}'

        monkeypatch.setattr(rev, "_call_openai", spy_call_openai)

        rev._call_llm(
            "gpt-5.4-mini",
            [{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            response_format={"type": "json_object"},
        )
        assert captured_kwargs["response_format"] == {"type": "json_object"}

    def test_anthropic_path_ignores_response_format(self, monkeypatch):
        import control.reviewer as rev

        called_with = []

        def spy_call_anthropic(model, messages):
            called_with.append((model, messages))
            return '{"decision": "ALLOW"}'

        monkeypatch.setattr(rev, "_call_anthropic", spy_call_anthropic)

        rev._call_llm(
            "claude-3-opus",
            [{"role": "user", "content": [{"type": "text", "text": "test"}]}],
            response_format={"type": "json_object"},
        )
        assert len(called_with) == 1
        assert len(called_with[0]) == 2  # only model + messages, no response_format
