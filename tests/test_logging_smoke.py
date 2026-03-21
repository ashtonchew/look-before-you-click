"""Smoke tests for control/logging.py -- Group 3 fixes."""

import json
import os
import tempfile

from control.logging import ControlLogger


def _make_logger(tmpdir):
    config = {
        "enabled": True,
        "router_mode": "critical_only",
        "controller_mode": "allow_or_terminate",
        "include_visual_context": True,
        "legibility_enabled": False,
        "fail_closed_on_review_error": True,
    }
    return ControlLogger(tmpdir, "test_task", "chrome", config)


class TestReviewPackageUniqueness:
    def test_same_step_creates_unique_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = _make_logger(tmpdir)
            pkg1 = {"instruction": "pkg1", "obs": {}}
            pkg2 = {"instruction": "pkg2", "obs": {}}
            logger.save_review_package(pkg1, step_idx=0)
            logger.save_review_package(pkg2, step_idx=0)

            packages_dir = os.path.join(tmpdir, "review_packages")
            files = sorted(os.listdir(packages_dir))
            assert files == ["step_0_0.json", "step_0_1.json"]

            with open(os.path.join(packages_dir, "step_0_0.json")) as f:
                assert json.load(f)["instruction"] == "pkg1"
            with open(os.path.join(packages_dir, "step_0_1.json")) as f:
                assert json.load(f)["instruction"] == "pkg2"

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
                "reviewer_result": {"allow": False, "risk_score": 0.9,
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
                "reviewer_result": {"allow": False, "risk_score": 0.9,
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
                "reviewer_result": {"allow": True, "risk_score": 0.1,
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
