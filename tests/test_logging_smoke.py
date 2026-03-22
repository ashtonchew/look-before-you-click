"""Smoke tests for control/logging.py."""

import json
import os
import tempfile

from control.logging import ControlLogger, build_control_event


def _make_logger(tmpdir, **config_overrides):
    config = {
        "enabled": True,
        "router_mode": "critical_only",
        "controller_mode": "allow_or_terminate",
        "include_visual_context": True,
        "legibility_enabled": False,
        "fail_closed_on_review_error": True,
    }
    config.update(config_overrides)
    return ControlLogger(tmpdir, "test_task", "chrome", config)


class TestReviewPackageUniqueness:
    def test_same_step_creates_unique_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            pkg1 = {"instruction": "pkg1", "obs": {}}
            pkg2 = {"instruction": "pkg2", "obs": {}}
            path1 = logger.save_review_package(pkg1, step_idx=0)
            path2 = logger.save_review_package(pkg2, step_idx=0)

            packages_dir = os.path.join(tmpdir, "review_packages")
            files = sorted(os.listdir(packages_dir))
            assert files == ["step_0_0.json", "step_0_1.json"]

            with open(os.path.join(packages_dir, "step_0_0.json")) as f:
                assert json.load(f)["instruction"] == "pkg1"
            with open(os.path.join(packages_dir, "step_0_1.json")) as f:
                assert json.load(f)["instruction"] == "pkg2"

            # save_review_package now returns path
            assert path1.endswith("step_0_0.json")
            assert path2.endswith("step_0_1.json")

    def test_different_steps_start_at_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            logger.save_review_package({"obs": {}}, step_idx=0)
            logger.save_review_package({"obs": {}}, step_idx=1)

            packages_dir = os.path.join(tmpdir, "review_packages")
            files = sorted(os.listdir(packages_dir))
            assert files == ["step_0_0.json", "step_1_0.json"]


class TestBlockedCount:
    def test_log_event_does_not_increment_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "BLOCK", "risk_score": 0.9,
                                    "primary_reason": "bad", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": False},
            }
            logger.log_event(event)
            # log_event should NOT increment blocked_count
            assert logger.blocked_count == 0

    def test_log_termination_increments_blocked_once(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            decision = {"execute": False, "termination_reason": "unsafe_action"}
            logger.log_termination(decision, step_idx=0, action="click(100,200)")
            assert logger.blocked_count == 1

    def test_no_double_count_on_block_then_terminate(self):
        """Simulate the actual runtime flow: log_event + log_termination for same action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "BLOCK", "risk_score": 0.9,
                                    "primary_reason": "bad", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": False},
            }
            logger.log_event(event)
            decision = {"execute": False, "termination_reason": "bad"}
            logger.log_termination(decision, step_idx=0, action="click(100,200)")
            # Should be exactly 1, not 2
            assert logger.blocked_count == 1


class TestEventCounting:
    def test_critical_count_incremented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "ALLOW", "risk_score": 0.1,
                                    "primary_reason": "ok", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": True},
            }
            logger.log_event(event)
            assert logger.critical_count == 1
            assert logger.review_count == 1

    def test_review_count_not_incremented_without_reviewer_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": None,
                "controller_decision": {"execute": False},
            }
            logger.log_event(event)
            assert logger.review_count == 0

    def test_resample_count_incremented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "RESAMPLE", "risk_score": 0.6,
                                    "primary_reason": "suspicious", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": False, "resample_requested": True},
                "resample_attempted": True,
                "final_action_source": "untrusted_resample",
            }
            logger.log_event(event)
            assert logger.resample_count == 1
            assert logger.action_source_counts["untrusted_resample"] == 1

    def test_trusted_fallback_count_incremented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "DEFER_TO_TRUSTED", "risk_score": 0.7,
                                    "primary_reason": "ambiguous", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": True},
                "trusted_fallback_attempted": True,
                "final_action_source": "trusted_fallback",
            }
            logger.log_event(event)
            assert logger.trusted_fallback_count == 1
            assert logger.action_source_counts["trusted_fallback"] == 1


    def test_resample_allowed_non_critical_incremented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "RESAMPLE", "risk_score": 0.6,
                                    "primary_reason": "suspicious", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": True, "resample_requested": True,
                                        "resample_rerouted_non_critical": True},
                "resample_attempted": True,
                "resample_action": "click(50, 50)",
                "resample_reviewer_result": {"decision": "NOT_CRITICAL",
                                             "note": "resampled action routed as non-critical"},
                "final_action_source": "untrusted_resample",
            }
            logger.log_event(event)
            assert logger.resample_allowed_non_critical == 1
            assert logger.resample_allowed_after_review == 0
            assert logger.resample_blocked_after_review == 0

    def test_resample_allowed_after_review_incremented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "RESAMPLE", "risk_score": 0.6,
                                    "primary_reason": "suspicious", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": True, "resample_requested": True},
                "resample_attempted": True,
                "resample_action": "click(50, 50)",
                "resample_reviewer_result": {"decision": "ALLOW", "risk_score": 0.2,
                                             "primary_reason": "safe", "evidence": []},
                "final_action_source": "untrusted_resample",
            }
            logger.log_event(event)
            assert logger.resample_allowed_non_critical == 0
            assert logger.resample_allowed_after_review == 1
            assert logger.resample_blocked_after_review == 0

    def test_resample_blocked_after_review_incremented(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "RESAMPLE", "risk_score": 0.6,
                                    "primary_reason": "suspicious", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": False, "resample_requested": True},
                "resample_attempted": True,
                "resample_action": "click(50, 50)",
                "resample_reviewer_result": {"decision": "BLOCK", "risk_score": 0.9,
                                             "primary_reason": "still dangerous", "evidence": []},
                "final_action_source": None,
            }
            logger.log_event(event)
            assert logger.resample_allowed_non_critical == 0
            assert logger.resample_allowed_after_review == 0
            assert logger.resample_blocked_after_review == 1
            assert logger.resample_failed == 0

    def test_resample_failed_incremented(self):
        """Predict failed or returned no actions -- no re-review occurred."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            event = {
                "router_decision": {"critical": True},
                "reviewer_result": {"decision": "RESAMPLE", "risk_score": 0.6,
                                    "primary_reason": "suspicious", "evidence": [],
                                    "safer_alternative": None},
                "controller_decision": {"execute": False, "resample_requested": True},
                "resample_attempted": True,
                "resample_action": None,
                "resample_reviewer_result": None,
                "final_action_source": None,
            }
            logger.log_event(event)
            assert logger.resample_failed == 1
            assert logger.resample_allowed_non_critical == 0
            assert logger.resample_allowed_after_review == 0
            assert logger.resample_blocked_after_review == 0


class TestSummary:
    def test_summary_includes_new_counters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir, controller_mode="allow_or_resample_once")
            summary = logger.build_summary()
            assert "resample_count" in summary
            assert "trusted_fallback_count" in summary
            assert "resample_allowed_non_critical" in summary
            assert "resample_allowed_after_review" in summary
            assert "resample_blocked_after_review" in summary
            assert "resample_failed" in summary
            assert summary["resample_count"] == 0
            assert summary["trusted_fallback_count"] == 0
            assert summary["control_mode"] == "allow_or_resample_once"


class TestBuildControlEvent:
    def test_builds_complete_event(self):
        episode = {
            "task_id": "t1", "domain": "chrome", "step_index": 0,
            "raw_action": "click(100, 200)",
            "normalized_action": {"primary_kind": "click"},
            "router_decision": {"critical": True},
            "legibility_report": None,
            "reviewer_result": {"decision": "ALLOW"},
            "review_latency_ms": 500,
            "reviewer_model": "gpt-4o",
        }
        decision = {"execute": True, "was_critical": True}
        event = build_control_event(
            episode=episode,
            controller_decision=decision,
            final_action="click(100, 200)",
            final_action_source="untrusted",
        )
        assert event["task_id"] == "t1"
        assert event["final_action"] == "click(100, 200)"
        assert event["final_action_source"] == "untrusted"
        assert event["resample_attempted"] is False
        assert event["trusted_fallback_attempted"] is False
        assert event["controller_decision"] == decision

    def test_builds_fallback_event_with_result(self):
        """Blocker 4: trusted_fallback_result must be preserved in the event."""
        episode = {
            "task_id": "t1", "domain": "chrome", "step_index": 0,
            "raw_action": "pyautogui.click(100, 200)",
            "normalized_action": {"primary_kind": "click"},
            "router_decision": {"critical": True},
            "legibility_report": None,
            "reviewer_result": {"decision": "DEFER_TO_TRUSTED"},
            "review_latency_ms": 400,
            "reviewer_model": "gpt-4o",
        }
        decision = {"execute": True, "was_critical": True}
        fallback = {
            "action": "pyautogui.click(50, 50)",
            "reason": "safer target",
            "confidence": 0.85,
        }
        event = build_control_event(
            episode=episode,
            controller_decision=decision,
            final_action="pyautogui.click(50, 50)",
            final_action_source="trusted_fallback",
            trusted_fallback_attempted=True,
            trusted_fallback_result=fallback,
        )
        assert event["trusted_fallback_attempted"] is True
        assert event["trusted_fallback_result"] is not None
        assert event["trusted_fallback_result"]["action"] == "pyautogui.click(50, 50)"
        assert event["final_action_source"] == "trusted_fallback"

    def test_builds_resample_event(self):
        episode = {
            "task_id": "t1", "domain": "chrome", "step_index": 0,
            "raw_action": "click(100, 200)",
            "normalized_action": {"primary_kind": "click"},
            "router_decision": {"critical": True},
            "reviewer_result": {"decision": "RESAMPLE"},
        }
        decision = {"execute": True, "was_critical": True}
        event = build_control_event(
            episode=episode,
            controller_decision=decision,
            final_action="click(50, 50)",
            final_action_source="untrusted_resample",
            resample_attempted=True,
            resample_action="click(50, 50)",
            resample_reviewer_result={"decision": "ALLOW"},
        )
        assert event["resample_attempted"] is True
        assert event["resample_action"] == "click(50, 50)"
        assert event["final_action_source"] == "untrusted_resample"
