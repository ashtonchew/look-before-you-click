"""Contract tests for control/controller.py -- Group 6 fixes.

Verifies the controller signature and return shape match the spec.
"""

import inspect

from control.controller import review, set_logger


class TestReviewSignature:
    def test_nine_parameters(self):
        """review() must have exactly 9 parameters matching the spec."""
        sig = inspect.signature(review)
        params = list(sig.parameters.keys())
        assert params == [
            "instruction", "obs", "raw_response", "raw_action",
            "recent_history", "step_idx", "task_id", "domain", "config",
        ]

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

    def test_non_critical_return_shape(self):
        """Non-critical actions return execute, termination_reason, and was_critical."""
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
        assert set(result.keys()) == {"execute", "termination_reason", "was_critical"}
        assert result["execute"] is True

    def test_unparsable_return_shape(self):
        """Unparsable actions return the standard ControllerDecision shape."""
        result = review(
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
        assert set(result.keys()) == {"execute", "termination_reason", "was_critical"}
        assert result["execute"] is False
        assert result["termination_reason"] == "unparsable_action"

    def test_disabled_return_shape(self):
        result = review(
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
        assert set(result.keys()) == {"execute", "termination_reason", "was_critical"}


class TestSetLogger:
    def test_set_logger_exists(self):
        """set_logger is callable."""
        assert callable(set_logger)
