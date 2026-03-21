"""Smoke tests for control/controller.py -- Group 1 fixes."""

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
        result = review(
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
        assert result["execute"] is True
        assert result["termination_reason"] is None

    def test_enabled_config_proceeds(self):
        config = _base_config(enabled=True)
        result = review(
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
        assert result["execute"] is True


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
        result = review(
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
        assert result["execute"] is True

    def test_done_not_critical_in_always_mode(self):
        config = _base_config(router_mode="always")
        result = review(
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
        assert result["execute"] is True

    def test_fail_not_critical_in_always_mode(self):
        config = _base_config(router_mode="always")
        result = review(
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
        assert result["execute"] is True


class TestA11yLinearizeFailure:
    @patch("control.controller._linearize_tree", side_effect=Exception("bad XML"))
    def test_linearize_crash_continues_with_no_target(self, mock_linearize):
        """If _linearize_tree raises, the controller must continue with target=None."""
        config = _base_config()
        obs = {"screenshot": b"fake", "accessibility_tree": "<malformed>"}
        result = review(
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
        assert result["execute"] is True
