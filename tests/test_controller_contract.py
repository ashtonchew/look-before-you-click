"""Contract tests for control/controller.py.

Verifies the controller signature and return shape match the spec.
"""

import inspect

from control.controller import review, set_logger


class TestReviewSignature:
    def test_ten_parameters(self):
        """review() must have exactly 10 parameters matching the spec."""
        sig = inspect.signature(review)
        params = list(sig.parameters.keys())
        assert params == [
            "instruction", "obs", "raw_response", "raw_action",
            "recent_history", "step_idx", "task_id", "domain", "config",
            "action_source_hint",
        ]

    def test_action_source_hint_has_default(self):
        """action_source_hint must default to 'untrusted'."""
        sig = inspect.signature(review)
        default = sig.parameters["action_source_hint"].default
        assert default == "untrusted"

    def test_no_control_logger_param(self):
        sig = inspect.signature(review)
        assert "control_logger" not in sig.parameters


class TestReturnShape:
    def _base_config(self, **overrides):
        cfg = {
            "enabled": True,
            "router_mode": "critical_only",
            "controller_mode": "allow_or_terminate",
            "include_visual_context": True,
            "legibility_enabled": False,
            "fail_closed_on_review_error": True,
            "critical_keywords_path": None,
        }
        cfg.update(overrides)
        return cfg

    _DECISION_KEYS = {
        "execute", "termination_reason", "was_critical",
        "reviewer_decision", "action_to_execute", "action_source",
        "resample_requested", "trusted_fallback_requested",
    }

    def test_non_critical_return_shape(self):
        """Non-critical actions return (ControllerDecision, None)."""
        result = review(
            instruction="test",
            obs={"screenshot": b"", "accessibility_tree": ""},
            raw_response="resp",
            raw_action="WAIT",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=self._base_config(),
        )
        assert isinstance(result, tuple)
        decision, episode = result
        assert set(decision.keys()) == self._DECISION_KEYS
        assert decision["execute"] is True
        assert decision["was_critical"] is False
        assert decision["action_to_execute"] == "WAIT"
        assert decision["action_source"] == "untrusted"
        assert episode is None

    def test_unparsable_return_shape(self):
        """Unparsable actions return (ControllerDecision, None)."""
        decision, episode = review(
            instruction="test",
            obs={"screenshot": b"", "accessibility_tree": ""},
            raw_response="resp",
            raw_action="some garbage",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=self._base_config(),
        )
        assert set(decision.keys()) == self._DECISION_KEYS
        assert decision["execute"] is False
        assert decision["termination_reason"] == "unparsable_action"
        assert episode is None

    def test_disabled_return_shape(self):
        decision, episode = review(
            instruction="test",
            obs={"screenshot": b"", "accessibility_tree": ""},
            raw_response="resp",
            raw_action="WAIT",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=self._base_config(enabled=False),
        )
        assert set(decision.keys()) == self._DECISION_KEYS
        assert decision["execute"] is True
        assert episode is None


class TestSetLogger:
    def test_set_logger_exists(self):
        """set_logger is callable."""
        assert callable(set_logger)
