"""Tests for controller.py policy application with mocked reviewer.

Covers:
- allow_or_terminate: ALLOW executes, BLOCK terminates, fail-closed on error
- allow_or_resample_once: RESAMPLE signals runtime, BLOCK terminates
- allow_or_trusted_fallback_once: DEFER_TO_TRUSTED invokes fallback, null action terminates
- Decision clamping: out-of-mode decisions are clamped to BLOCK
- Return shape: all returns are (ControllerDecision, ReviewEpisode|None) tuples
- Logging: events logged for critical actions, no crash without logger
"""

import pytest
from unittest.mock import patch, MagicMock

from control.controller import review, set_logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_config(**overrides):
    cfg = {
        "enabled": True,
        "router_mode": "critical_only",
        "controller_mode": "allow_or_terminate",
        "include_visual_context": False,
        "legibility_enabled": False,
        "fail_closed_on_review_error": True,
        "critical_keywords_path": None,
    }
    cfg.update(overrides)
    return cfg


def _base_obs():
    return {"screenshot": b"fake", "accessibility_tree": ""}


def _fake_normalized():
    return {
        "raw_action": "import pyautogui; pyautogui.click(100, 200)",
        "primary_kind": "click",
        "x": 100.0, "y": 200.0,
        "text": None, "keys": None, "button": None, "special_token": None,
        "target_matched": True,
        "target_tag": "push-button",
        "target_name": "Send",
        "target_text": "Send",
        "target_bounds": {"x": 90, "y": 190, "w": 60, "h": 30},
        "target_match_method": "contains_point",
    }


def _critical_route():
    return {"critical": True, "family": "send_submit_share", "reasons": ["Send button"], "confidence": 0.9}


def _not_critical_route():
    return {"critical": False, "family": None, "reasons": [], "confidence": 1.0}


def _reviewer_allow():
    return {"decision": "ALLOW", "risk_score": 0.1, "primary_reason": "aligned with task", "evidence": ["Send button for email"], "safer_alternative": None}


def _reviewer_block(reason="data exfiltration risk"):
    return {"decision": "BLOCK", "risk_score": 0.9, "primary_reason": reason, "evidence": ["sending to external"], "safer_alternative": "cancel the action"}


def _reviewer_resample():
    return {"decision": "RESAMPLE", "risk_score": 0.6, "primary_reason": "ambiguous target", "evidence": ["unclear element"], "safer_alternative": None}


def _reviewer_defer():
    return {"decision": "DEFER_TO_TRUSTED", "risk_score": 0.7, "primary_reason": "high impact action", "evidence": ["sensitive data visible"], "safer_alternative": None}


_RAW_ACTION = "import pyautogui; pyautogui.click(100, 200)"

# Shared patches
_NORMALIZE_PATCH = patch("control.controller.normalize", return_value=_fake_normalized())
_ROUTE_CRITICAL = patch("control.controller.route", return_value=_critical_route())
_ROUTE_NOT_CRITICAL = patch("control.controller.route", return_value=_not_critical_route())
_LEGIBILITY_PATCH = patch("control.controller.generate_legibility", return_value=None)


def _call_review(config_overrides=None, reviewer_return=None, reviewer_side_effect=None):
    """Helper to call review with standard args and mocked internals."""
    config = _base_config(**(config_overrides or {}))
    with patch("control.controller.normalize", return_value=_fake_normalized()), \
         patch("control.controller.route", return_value=_critical_route()), \
         patch("control.controller.generate_legibility", return_value=None):
        if reviewer_side_effect:
            with patch("control.controller.reviewer_review", side_effect=reviewer_side_effect):
                return review(
                    "send email", _base_obs(), "resp", _RAW_ACTION,
                    [], 0, "t1", "chrome", config,
                )
        else:
            with patch("control.controller.reviewer_review", return_value=reviewer_return):
                return review(
                    "send email", _base_obs(), "resp", _RAW_ACTION,
                    [], 0, "t1", "chrome", config,
                )


# ---------------------------------------------------------------------------
# Return shape validation
# ---------------------------------------------------------------------------


class TestReturnShape:
    def test_returns_tuple(self):
        set_logger(None)
        result = _call_review(reviewer_return=_reviewer_allow())
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_critical_action_returns_episode(self):
        set_logger(None)
        decision, episode = _call_review(reviewer_return=_reviewer_allow())
        assert episode is not None
        assert "task_id" in episode
        assert "reviewer_result" in episode

    def test_non_critical_returns_none_episode(self):
        set_logger(None)
        config = _base_config()
        with patch("control.controller.normalize", return_value=_fake_normalized()), \
             patch("control.controller.route", return_value=_not_critical_route()):
            decision, episode = review(
                "move mouse", _base_obs(), "resp", _RAW_ACTION,
                [], 0, "t1", "chrome", config,
            )
        assert episode is None
        assert decision["execute"] is True

    def test_decision_has_eight_keys(self):
        set_logger(None)
        decision, _ = _call_review(reviewer_return=_reviewer_allow())
        expected_keys = {
            "execute", "termination_reason", "was_critical",
            "reviewer_decision", "action_to_execute", "action_source",
            "resample_requested", "trusted_fallback_requested",
        }
        assert set(decision.keys()) == expected_keys

    def test_disabled_returns_tuple_with_none_episode(self):
        set_logger(None)
        decision, episode = review(
            "test", _base_obs(), "resp", "WAIT",
            [], 0, "t1", "chrome", _base_config(enabled=False),
        )
        assert decision["execute"] is True
        assert episode is None


# ---------------------------------------------------------------------------
# allow_or_terminate mode
# ---------------------------------------------------------------------------


class TestAllowOrTerminate:
    def test_allow_executes(self):
        set_logger(None)
        decision, episode = _call_review(reviewer_return=_reviewer_allow())
        assert decision["execute"] is True
        assert decision["was_critical"] is True
        assert decision["reviewer_decision"] == "ALLOW"
        assert decision["action_to_execute"] == _RAW_ACTION

    def test_block_terminates(self):
        set_logger(None)
        decision, episode = _call_review(reviewer_return=_reviewer_block("exfil"))
        assert decision["execute"] is False
        assert decision["termination_reason"] == "exfil"
        assert decision["reviewer_decision"] == "BLOCK"

    def test_fail_closed_on_reviewer_error(self):
        set_logger(None)
        decision, episode = _call_review(
            config_overrides={"fail_closed_on_review_error": True},
            reviewer_side_effect=RuntimeError("API down"),
        )
        assert decision["execute"] is False
        assert decision["termination_reason"] == "review_error_fail_closed"
        assert episode is not None  # episode still created for logging

    def test_reraises_when_not_fail_closed(self):
        set_logger(None)
        with pytest.raises(RuntimeError, match="API down"):
            _call_review(
                config_overrides={"fail_closed_on_review_error": False},
                reviewer_side_effect=RuntimeError("API down"),
            )

    def test_resample_decision_clamped_to_block(self):
        """RESAMPLE is not valid in allow_or_terminate -- clamped to BLOCK."""
        set_logger(None)
        decision, _ = _call_review(reviewer_return=_reviewer_resample())
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "BLOCK"

    def test_defer_decision_clamped_to_block(self):
        """DEFER_TO_TRUSTED is not valid in allow_or_terminate -- clamped to BLOCK."""
        set_logger(None)
        decision, _ = _call_review(reviewer_return=_reviewer_defer())
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "BLOCK"


# ---------------------------------------------------------------------------
# allow_or_resample_once mode
# ---------------------------------------------------------------------------


class TestAllowOrResampleOnce:
    def test_resample_signals_runtime(self):
        set_logger(None)
        decision, episode = _call_review(
            config_overrides={"controller_mode": "allow_or_resample_once"},
            reviewer_return=_reviewer_resample(),
        )
        assert decision["resample_requested"] is True
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "RESAMPLE"
        assert episode is not None

    def test_allow_still_executes(self):
        set_logger(None)
        decision, _ = _call_review(
            config_overrides={"controller_mode": "allow_or_resample_once"},
            reviewer_return=_reviewer_allow(),
        )
        assert decision["execute"] is True
        assert decision["reviewer_decision"] == "ALLOW"

    def test_block_still_terminates(self):
        set_logger(None)
        decision, _ = _call_review(
            config_overrides={"controller_mode": "allow_or_resample_once"},
            reviewer_return=_reviewer_block(),
        )
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "BLOCK"

    def test_defer_clamped_to_block_in_resample_mode(self):
        set_logger(None)
        decision, _ = _call_review(
            config_overrides={"controller_mode": "allow_or_resample_once"},
            reviewer_return=_reviewer_defer(),
        )
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "BLOCK"


# ---------------------------------------------------------------------------
# allow_or_trusted_fallback_once mode
# ---------------------------------------------------------------------------


class TestAllowOrTrustedFallbackOnce:
    def test_defer_calls_fallback_and_executes_valid_action(self):
        set_logger(None)
        fallback = {"action": "import pyautogui; pyautogui.press('escape')", "reason": "safe exit", "confidence": 0.9}
        with patch("control.controller.normalize", return_value=_fake_normalized()), \
             patch("control.controller.route", return_value=_critical_route()), \
             patch("control.controller.generate_legibility", return_value=None), \
             patch("control.controller.reviewer_review", return_value=_reviewer_defer()), \
             patch("control.controller.reviewer_trusted_fallback", return_value=fallback):
            decision, episode = review(
                "test", _base_obs(), "resp", _RAW_ACTION,
                [], 0, "t1", "chrome",
                _base_config(controller_mode="allow_or_trusted_fallback_once"),
            )
        assert decision["execute"] is True
        assert decision["action_source"] == "trusted_fallback"
        assert decision["trusted_fallback_requested"] is True
        assert decision["action_to_execute"] == "import pyautogui; pyautogui.press('escape')"

    def test_null_fallback_action_terminates(self):
        set_logger(None)
        fallback = {"action": None, "reason": "no safe action", "confidence": 0.3}
        with patch("control.controller.normalize", return_value=_fake_normalized()), \
             patch("control.controller.route", return_value=_critical_route()), \
             patch("control.controller.generate_legibility", return_value=None), \
             patch("control.controller.reviewer_review", return_value=_reviewer_defer()), \
             patch("control.controller.reviewer_trusted_fallback", return_value=fallback):
            decision, episode = review(
                "test", _base_obs(), "resp", _RAW_ACTION,
                [], 0, "t1", "chrome",
                _base_config(controller_mode="allow_or_trusted_fallback_once"),
            )
        assert decision["execute"] is False
        assert decision["trusted_fallback_requested"] is True
        assert "empty" in decision["termination_reason"] or "fallback" in decision["termination_reason"]

    def test_fallback_error_terminates(self):
        set_logger(None)
        with patch("control.controller.normalize", return_value=_fake_normalized()), \
             patch("control.controller.route", return_value=_critical_route()), \
             patch("control.controller.generate_legibility", return_value=None), \
             patch("control.controller.reviewer_review", return_value=_reviewer_defer()), \
             patch("control.controller.reviewer_trusted_fallback", side_effect=RuntimeError("API down")):
            decision, episode = review(
                "test", _base_obs(), "resp", _RAW_ACTION,
                [], 0, "t1", "chrome",
                _base_config(controller_mode="allow_or_trusted_fallback_once"),
            )
        assert decision["execute"] is False
        assert decision["trusted_fallback_requested"] is True
        assert "error" in decision["termination_reason"]

    def test_resample_clamped_to_block_in_fallback_mode(self):
        set_logger(None)
        decision, _ = _call_review(
            config_overrides={"controller_mode": "allow_or_trusted_fallback_once"},
            reviewer_return=_reviewer_resample(),
        )
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "BLOCK"


# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------


class TestLoggingIntegration:
    @_NORMALIZE_PATCH
    @_ROUTE_CRITICAL
    @_LEGIBILITY_PATCH
    @patch("control.controller.reviewer_review", return_value=_reviewer_allow())
    def test_review_package_saved_when_logger_set(self, _rev, _leg, _route, _norm):
        mock_logger = MagicMock()
        mock_logger.save_review_package.return_value = "/tmp/step_0_0.json"
        set_logger(mock_logger)
        try:
            review("test", _base_obs(), "resp", _RAW_ACTION, [], 0, "t1", "chrome", _base_config())
            mock_logger.save_review_package.assert_called_once()
            package = mock_logger.save_review_package.call_args[0][0]
            assert "controller_mode" in package
            assert "instruction" in package
        finally:
            set_logger(None)

    @_NORMALIZE_PATCH
    @_ROUTE_CRITICAL
    @_LEGIBILITY_PATCH
    @patch("control.controller.reviewer_review", return_value=_reviewer_allow())
    def test_no_logger_no_crash(self, _rev, _leg, _route, _norm):
        set_logger(None)
        decision, _ = review("test", _base_obs(), "resp", _RAW_ACTION, [], 0, "t1", "chrome", _base_config())
        assert decision["execute"] is True

    @_NORMALIZE_PATCH
    @_ROUTE_NOT_CRITICAL
    @patch("control.controller.reviewer_review")
    def test_non_critical_bypasses_reviewer(self, mock_rev, _route, _norm):
        set_logger(None)
        decision, episode = review("test", _base_obs(), "resp", _RAW_ACTION, [], 0, "t1", "chrome", _base_config())
        assert decision["execute"] is True
        assert decision["was_critical"] is False
        assert episode is None
        mock_rev.assert_not_called()
