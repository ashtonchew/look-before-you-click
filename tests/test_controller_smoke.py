"""Smoke tests for control/controller.py."""

import pytest
from unittest.mock import patch, MagicMock

from control.controller import review


def _base_config(**overrides):
    cfg = {
        "enabled": True,
        "router_mode": "critical_only",
        "controller_mode": "allow_or_terminate",
        "include_visual_context": True,
        "legibility_enabled": False,
        "fail_closed_on_review_error": True,
    }
    cfg.update(overrides)
    return cfg


def _base_obs():
    return {"screenshot": b"fake", "accessibility_tree": ""}


class TestEnabledGuard:
    def test_disabled_config_returns_execute_true(self):
        config = _base_config(enabled=False)
        decision, episode = review(
            instruction="test",
            obs=_base_obs(),
            raw_response="resp",
            raw_action="WAIT",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )
        assert decision["execute"] is True
        assert decision["termination_reason"] is None
        assert episode is None

    def test_enabled_config_proceeds(self):
        config = _base_config(enabled=True)
        decision, episode = review(
            instruction="test",
            obs=_base_obs(),
            raw_response="resp",
            raw_action="WAIT",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )
        # WAIT is a special token -> not critical -> execute=True
        assert decision["execute"] is True
        assert episode is None


class TestA11yLinearization:
    @patch("control.controller.parse_tree")
    @patch("control.controller.match_target")
    @patch("control.controller._linearize_tree")
    def test_parse_tree_receives_linearized_not_raw(
        self, mock_linearize, mock_match, mock_parse
    ):
        fake_xml = "<root><node/></root>"
        fake_linearized = "tag\tname\ttext\tcls\tdesc\t(10, 20)\t(30, 40)"
        mock_linearize.return_value = fake_linearized
        mock_parse.return_value = []
        mock_match.return_value = {
            "target_matched": False, "target_tag": None,
            "target_name": None, "target_text": None,
            "target_bounds": None, "target_match_method": "none",
        }

        config = _base_config()
        obs = {"screenshot": b"fake", "accessibility_tree": fake_xml}
        review(
            instruction="test",
            obs=obs,
            raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )

        # parse_tree should receive the linearized form, not raw XML
        mock_linearize.assert_called_once_with(fake_xml)
        mock_parse.assert_called_once_with(fake_linearized)


class TestAlwaysModeSpecialTokens:
    def test_wait_not_critical_in_always_mode(self):
        config = _base_config(router_mode="always")
        decision, episode = review(
            instruction="test",
            obs=_base_obs(),
            raw_response="resp",
            raw_action="WAIT",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )
        assert decision["execute"] is True
        assert episode is None

    def test_done_not_critical_in_always_mode(self):
        config = _base_config(router_mode="always")
        decision, episode = review(
            instruction="test",
            obs=_base_obs(),
            raw_response="resp",
            raw_action="DONE",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )
        assert decision["execute"] is True
        assert episode is None

    def test_fail_not_critical_in_always_mode(self):
        config = _base_config(router_mode="always")
        decision, episode = review(
            instruction="test",
            obs=_base_obs(),
            raw_response="resp",
            raw_action="FAIL",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )
        assert decision["execute"] is True
        assert episode is None


class TestA11yLinearizeFailure:
    @patch("control.controller._linearize_tree", side_effect=Exception("bad XML"))
    def test_linearize_crash_continues_with_no_target(self, mock_linearize):
        """If _linearize_tree raises, the controller must continue with target=None."""
        config = _base_config()
        obs = {"screenshot": b"fake", "accessibility_tree": "<malformed>"}
        decision, episode = review(
            instruction="test",
            obs=obs,
            raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[],
            step_idx=0,
            task_id="t1",
            domain="chrome",
            config=config,
        )
        # Must not crash -- should proceed with no target match
        assert decision["execute"] is True


class TestPolicyMapping:
    """Test the 3-mode policy dispatch with mocked reviewer."""

    @patch("control.controller.reviewer_review")
    @patch("control.controller.route")
    def test_allow_decision_executes(self, mock_route, mock_reviewer):
        mock_route.return_value = {"critical": True, "family": "send", "reasons": ["email"], "confidence": 0.9}
        mock_reviewer.return_value = {
            "decision": "ALLOW", "risk_score": 0.1,
            "primary_reason": "safe", "evidence": [], "safer_alternative": None,
        }
        config = _base_config()
        decision, episode = review(
            instruction="test", obs=_base_obs(), raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[], step_idx=0, task_id="t1", domain="chrome",
            config=config,
        )
        assert decision["execute"] is True
        assert decision["reviewer_decision"] == "ALLOW"
        assert decision["action_to_execute"] == "import pyautogui; pyautogui.click(100, 200)"
        assert episode is not None

    @patch("control.controller.reviewer_review")
    @patch("control.controller.route")
    def test_block_decision_terminates(self, mock_route, mock_reviewer):
        mock_route.return_value = {"critical": True, "family": "send", "reasons": ["email"], "confidence": 0.9}
        mock_reviewer.return_value = {
            "decision": "BLOCK", "risk_score": 0.9,
            "primary_reason": "malicious", "evidence": ["exfil"], "safer_alternative": None,
        }
        config = _base_config()
        decision, episode = review(
            instruction="test", obs=_base_obs(), raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[], step_idx=0, task_id="t1", domain="chrome",
            config=config,
        )
        assert decision["execute"] is False
        assert decision["reviewer_decision"] == "BLOCK"
        assert episode is not None

    @patch("control.controller.reviewer_review")
    @patch("control.controller.route")
    def test_resample_in_resample_mode(self, mock_route, mock_reviewer):
        mock_route.return_value = {"critical": True, "family": "send", "reasons": ["email"], "confidence": 0.9}
        mock_reviewer.return_value = {
            "decision": "RESAMPLE", "risk_score": 0.6,
            "primary_reason": "suspicious", "evidence": [], "safer_alternative": "try escape",
        }
        config = _base_config(controller_mode="allow_or_resample_once")
        decision, episode = review(
            instruction="test", obs=_base_obs(), raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[], step_idx=0, task_id="t1", domain="chrome",
            config=config,
        )
        assert decision["execute"] is False
        assert decision["resample_requested"] is True
        assert decision["reviewer_decision"] == "RESAMPLE"
        assert episode is not None

    @patch("control.controller.reviewer_review")
    @patch("control.controller.route")
    def test_resample_in_terminate_mode_becomes_block(self, mock_route, mock_reviewer):
        """RESAMPLE is not valid in allow_or_terminate -- clamped to BLOCK."""
        mock_route.return_value = {"critical": True, "family": "send", "reasons": ["email"], "confidence": 0.9}
        mock_reviewer.return_value = {
            "decision": "RESAMPLE", "risk_score": 0.6,
            "primary_reason": "suspicious", "evidence": [], "safer_alternative": None,
        }
        config = _base_config(controller_mode="allow_or_terminate")
        decision, episode = review(
            instruction="test", obs=_base_obs(), raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[], step_idx=0, task_id="t1", domain="chrome",
            config=config,
        )
        assert decision["execute"] is False
        assert decision["resample_requested"] is False
        assert decision["reviewer_decision"] == "BLOCK"

    @patch("control.controller.reviewer_trusted_fallback")
    @patch("control.controller.reviewer_review")
    @patch("control.controller.route")
    def test_defer_in_fallback_mode_executes_trusted(self, mock_route, mock_reviewer, mock_fallback):
        mock_route.return_value = {"critical": True, "family": "send", "reasons": ["email"], "confidence": 0.9}
        mock_reviewer.return_value = {
            "decision": "DEFER_TO_TRUSTED", "risk_score": 0.7,
            "primary_reason": "ambiguous", "evidence": [], "safer_alternative": None,
        }
        mock_fallback.return_value = {
            "action": "import pyautogui; pyautogui.press('escape')",
            "reason": "safe cancel", "confidence": 0.9,
        }
        config = _base_config(controller_mode="allow_or_trusted_fallback_once")
        decision, episode = review(
            instruction="test", obs=_base_obs(), raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[], step_idx=0, task_id="t1", domain="chrome",
            config=config,
        )
        assert decision["execute"] is True
        assert decision["reviewer_decision"] == "DEFER_TO_TRUSTED"
        assert decision["action_source"] == "trusted_fallback"
        assert decision["action_to_execute"] == "import pyautogui; pyautogui.press('escape')"
        assert decision["trusted_fallback_requested"] is True

    @patch("control.controller.reviewer_trusted_fallback")
    @patch("control.controller.reviewer_review")
    @patch("control.controller.route")
    def test_defer_with_empty_fallback_terminates(self, mock_route, mock_reviewer, mock_fallback):
        mock_route.return_value = {"critical": True, "family": "send", "reasons": ["email"], "confidence": 0.9}
        mock_reviewer.return_value = {
            "decision": "DEFER_TO_TRUSTED", "risk_score": 0.7,
            "primary_reason": "ambiguous", "evidence": [], "safer_alternative": None,
        }
        mock_fallback.return_value = {
            "action": None, "reason": "no safe action", "confidence": 0.1,
        }
        config = _base_config(controller_mode="allow_or_trusted_fallback_once")
        decision, episode = review(
            instruction="test", obs=_base_obs(), raw_response="resp",
            raw_action="import pyautogui; pyautogui.click(100, 200)",
            recent_history=[], step_idx=0, task_id="t1", domain="chrome",
            config=config,
        )
        assert decision["execute"] is False
        assert decision["termination_reason"] == "trusted_fallback_empty"
        assert decision["trusted_fallback_requested"] is True
