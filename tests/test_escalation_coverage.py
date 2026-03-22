"""Tests for logging/summary escalation metadata and aggregate B4R/B4T handling.

Covers:
- build_summary includes resample_count, trusted_fallback_count, control_mode
- write_summary JSON validity
- Latency accumulation across events
- build_control_event shape for escalation fields
- infer_baseline B4, B4R, B4T distinct labels
- B4R/B4T config file validation
- CSV_COLUMNS includes escalation columns
"""

import json
import os
import tempfile

import pytest

from control.logging import ControlLogger, build_control_event
from analysis.aggregate import infer_baseline, CSV_COLUMNS
from control.types import review_episode, normalized_action, router_decision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_logger(tmpdir, **config_overrides):
    config = {
        "enabled": True,
        "router_mode": "critical_only",
        "controller_mode": "allow_or_terminate",
        "include_visual_context": True,
        "legibility_enabled": True,
        "fail_closed_on_review_error": True,
    }
    config.update(config_overrides)
    return ControlLogger(tmpdir, "test_task", "chrome", config)


def _make_event(review_latency_ms=None, critical=True, reviewer_result=None,
                resample_attempted=False, trusted_fallback_attempted=False,
                final_action_source=None):
    return {
        "router_decision": {"critical": critical},
        "reviewer_result": reviewer_result or {
            "decision": "ALLOW", "risk_score": 0.1,
            "primary_reason": "ok", "evidence": [],
            "safer_alternative": None,
        },
        "controller_decision": {"execute": True},
        "review_latency_ms": review_latency_ms,
        "resample_attempted": resample_attempted,
        "trusted_fallback_attempted": trusted_fallback_attempted,
        "final_action_source": final_action_source,
    }


# ---------------------------------------------------------------------------
# Summary fields
# ---------------------------------------------------------------------------


class TestSummaryFields:
    def test_summary_includes_control_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            summary = logger.build_summary()
            assert "control_mode" in summary

    def test_summary_control_mode_from_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir, controller_mode="allow_or_resample_once")
            summary = logger.build_summary()
            assert summary["control_mode"] == "allow_or_resample_once"

    def test_summary_includes_resample_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            summary = logger.build_summary()
            assert "resample_count" in summary
            assert summary["resample_count"] == 0

    def test_summary_includes_trusted_fallback_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            summary = logger.build_summary()
            assert "trusted_fallback_count" in summary
            assert summary["trusted_fallback_count"] == 0

    def test_summary_has_fourteen_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            summary = logger.build_summary()
            expected = {
                "task_id", "domain", "control_mode", "router_mode",
                "include_visual_context", "legibility_enabled",
                "review_count", "critical_count", "blocked_count",
                "resample_count", "trusted_fallback_count",
                "review_latency_ms_total", "terminated_by_control",
                "termination_reason",
            }
            assert set(summary.keys()) == expected

    def test_write_summary_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            logger.log_event(_make_event(review_latency_ms=150))
            logger.write_summary()

            summary_path = os.path.join(tmpdir, "control_summary.json")
            assert os.path.exists(summary_path)
            with open(summary_path) as f:
                data = json.load(f)
            assert data["task_id"] == "test_task"
            assert data["review_count"] == 1

    def test_latency_accumulation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            logger.log_event(_make_event(review_latency_ms=100))
            logger.log_event(_make_event(review_latency_ms=250))
            summary = logger.build_summary()
            assert summary["review_latency_ms_total"] == 350


# ---------------------------------------------------------------------------
# Escalation counter tracking
# ---------------------------------------------------------------------------


class TestEscalationCounters:
    def test_resample_count_tracked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            logger.log_event(_make_event(resample_attempted=True))
            logger.log_event(_make_event(resample_attempted=False))
            assert logger.resample_count == 1

    def test_trusted_fallback_count_tracked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            logger.log_event(_make_event(trusted_fallback_attempted=True))
            assert logger.trusted_fallback_count == 1

    def test_action_source_counts_tracked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            logger.log_event(_make_event(final_action_source="untrusted"))
            logger.log_event(_make_event(final_action_source="trusted_fallback"))
            logger.log_event(_make_event(final_action_source="untrusted"))
            assert logger.action_source_counts["untrusted"] == 2
            assert logger.action_source_counts["trusted_fallback"] == 1


# ---------------------------------------------------------------------------
# build_control_event shape
# ---------------------------------------------------------------------------


class TestBuildControlEvent:
    def test_event_has_escalation_fields(self):
        na = normalized_action("pyautogui.click(1,2)", "click", x=1.0, y=2.0)
        rd = router_decision(True, "send_submit_share", ["Send button"], 0.9)
        ep = review_episode("t1", "chrome", 0, "pyautogui.click(1,2)", na, rd)
        cd = {"execute": False, "termination_reason": "blocked"}

        event = build_control_event(
            episode=ep, controller_decision=cd,
            resample_attempted=True,
            resample_action="pyautogui.press('escape')",
            resample_reviewer_result={"decision": "BLOCK"},
        )
        assert event["resample_attempted"] is True
        assert event["resample_action"] == "pyautogui.press('escape')"
        assert event["trusted_fallback_attempted"] is False

    def test_event_has_fallback_fields(self):
        na = normalized_action("pyautogui.click(1,2)", "click", x=1.0, y=2.0)
        rd = router_decision(True, "send_submit_share", ["Send button"], 0.9)
        ep = review_episode("t1", "chrome", 0, "pyautogui.click(1,2)", na, rd)
        cd = {"execute": True, "termination_reason": None}

        fallback_result = {"action": "pyautogui.press('escape')", "reason": "safe", "confidence": 0.8}
        event = build_control_event(
            episode=ep, controller_decision=cd,
            trusted_fallback_attempted=True,
            trusted_fallback_result=fallback_result,
            final_action="pyautogui.press('escape')",
            final_action_source="trusted_fallback",
        )
        assert event["trusted_fallback_attempted"] is True
        assert event["trusted_fallback_result"]["action"] == "pyautogui.press('escape')"
        assert event["final_action_source"] == "trusted_fallback"

    def test_event_defaults_no_escalation(self):
        na = normalized_action("pyautogui.click(1,2)", "click", x=1.0, y=2.0)
        rd = router_decision(True, "send_submit_share", ["Send button"], 0.9)
        ep = review_episode("t1", "chrome", 0, "pyautogui.click(1,2)", na, rd)
        cd = {"execute": True}

        event = build_control_event(episode=ep, controller_decision=cd)
        assert event["resample_attempted"] is False
        assert event["trusted_fallback_attempted"] is False
        assert event["final_action"] is None
        assert event["final_action_source"] is None


# ---------------------------------------------------------------------------
# infer_baseline B4R/B4T label handling
# ---------------------------------------------------------------------------


class TestInferBaselineEscalation:
    def _b4_summary(self, controller_mode="allow_or_terminate"):
        return {
            "router_mode": "critical_only",
            "include_visual_context": True,
            "legibility_enabled": True,
            "control_mode": controller_mode,
        }

    def test_b4_for_terminate_mode(self):
        assert infer_baseline(self._b4_summary("allow_or_terminate"), "/fake") == "B4"

    def test_b4r_for_resample_mode(self):
        assert infer_baseline(self._b4_summary("allow_or_resample_once"), "/fake") == "B4R"

    def test_b4t_for_fallback_mode(self):
        assert infer_baseline(self._b4_summary("allow_or_trusted_fallback_once"), "/fake") == "B4T"

    def test_all_three_labels_distinct(self):
        b4 = infer_baseline(self._b4_summary("allow_or_terminate"), "/fake")
        b4r = infer_baseline(self._b4_summary("allow_or_resample_once"), "/fake")
        b4t = infer_baseline(self._b4_summary("allow_or_trusted_fallback_once"), "/fake")
        assert len({b4, b4r, b4t}) == 3

    def test_b0_when_no_summary(self):
        assert infer_baseline(None, "/fake") == "B0"

    def test_b1_always_language(self):
        summary = {"router_mode": "always", "include_visual_context": False}
        assert infer_baseline(summary, "/fake") == "B1"

    def test_b3_critical_no_legibility(self):
        summary = {"router_mode": "critical_only", "include_visual_context": True, "legibility_enabled": False}
        assert infer_baseline(summary, "/fake") == "B3"


# ---------------------------------------------------------------------------
# CSV columns include escalation fields
# ---------------------------------------------------------------------------


class TestCSVColumnsEscalation:
    def test_csv_has_resample_count(self):
        assert "resample_count" in CSV_COLUMNS

    def test_csv_has_trusted_fallback_count(self):
        assert "trusted_fallback_count" in CSV_COLUMNS


# ---------------------------------------------------------------------------
# B4R/B4T config files
# ---------------------------------------------------------------------------


class TestB4RB4TConfigs:
    _CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "..", "configs")

    def test_b4r_config_exists_and_valid(self):
        path = os.path.join(self._CONFIGS_DIR, "control_critical_legibility_resample_once.json")
        assert os.path.exists(path)
        with open(path) as f:
            cfg = json.load(f)
        assert cfg["controller_mode"] == "allow_or_resample_once"
        assert cfg["legibility_enabled"] is True

    def test_b4t_config_exists_and_valid(self):
        path = os.path.join(self._CONFIGS_DIR, "control_critical_legibility_trusted_fallback_once.json")
        assert os.path.exists(path)
        with open(path) as f:
            cfg = json.load(f)
        assert cfg["controller_mode"] == "allow_or_trusted_fallback_once"
        assert cfg["legibility_enabled"] is True
