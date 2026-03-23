"""Control protocol logging -- writes control_events.jsonl, control_summary.json, and review packages."""

import logging as _stdlib_logging
import json
import os

_logger = _stdlib_logging.getLogger("desktopenv.control")


class ControlLogger:
    """Manages control protocol log files for a single run."""

    def __init__(self, result_dir: str, task_id: str, domain: str, config: dict):
        self.result_dir = result_dir
        self.task_id = task_id
        self.domain = domain
        self.config = config

        # Create review packages directory
        self.packages_dir = os.path.join(result_dir, "review_packages")
        os.makedirs(self.packages_dir, exist_ok=True)

        # Paths
        self._events_path = os.path.join(result_dir, "control_events.jsonl")
        self._summary_path = os.path.join(result_dir, "control_summary.json")

        # Sub-index counters for unique review package filenames per step
        self._sub_idx = {}

        # Counters
        self.review_count = 0
        self.critical_count = 0
        self.blocked_count = 0
        self.resample_count = 0
        self.trusted_fallback_count = 0
        self.review_latency_ms_total = 0
        self.terminated_by_control = False
        self.termination_reason = None
        self.resample_allowed_non_critical = 0
        self.resample_allowed_after_review = 0
        self.resample_blocked_after_review = 0
        self.resample_failed = 0
        self.action_source_counts = {
            "untrusted": 0,
            "untrusted_resample": 0,
            "trusted_fallback": 0,
        }

    def log_event(self, event: dict) -> None:
        """Append one ControlEventLog record to control_events.jsonl."""
        # Update counters from event data
        router = event.get("router_decision", {})
        controller = event.get("controller_decision", {})

        if router.get("critical"):
            self.critical_count += 1
        if event.get("reviewer_result") is not None:
            self.review_count += 1
        if event.get("review_latency_ms") is not None:
            self.review_latency_ms_total += event["review_latency_ms"]
        if event.get("resample_attempted"):
            self.resample_count += 1
            if not event.get("resample_action"):
                # Predict failed or returned no actions -- no re-review occurred
                self.resample_failed += 1
            else:
                resample_rr = event.get("resample_reviewer_result") or {}
                if resample_rr.get("decision") == "NOT_CRITICAL":
                    self.resample_allowed_non_critical += 1
                elif controller.get("execute"):
                    self.resample_allowed_after_review += 1
                else:
                    self.resample_blocked_after_review += 1
        if event.get("trusted_fallback_attempted"):
            self.trusted_fallback_count += 1

        # Track action source
        source = event.get("final_action_source")
        if source and source in self.action_source_counts:
            self.action_source_counts[source] += 1

        with open(self._events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event))
            f.write("\n")
            f.flush()

        _logger.info(json.dumps({
            "event": "control_event_logged",
            "task_id": event.get("task_id"),
            "step": event.get("step_index"),
            "critical": router.get("critical"),
            "execute": controller.get("execute"),
        }))

    def save_review_package(self, package: dict, step_idx: int) -> str:
        """Write one review package JSON file to review_packages/.

        Returns the path to the saved file.
        """
        # Strip screenshot bytes before saving -- they are large and already saved as PNGs
        save_package = dict(package)
        if "obs" in save_package:
            save_package["obs"] = {
                k: v for k, v in save_package["obs"].items() if k != "screenshot"
            }

        sub = self._sub_idx.get(step_idx, 0)
        self._sub_idx[step_idx] = sub + 1
        path = os.path.join(self.packages_dir, f"step_{step_idx}_{sub}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_package, f, indent=2, default=str)

        return path

    def log_termination(self, decision: dict, step_idx: int, action: str) -> None:
        """Log a control-initiated termination."""
        self.terminated_by_control = True
        self.termination_reason = decision.get("termination_reason")
        self.blocked_count += 1

        _logger.info(json.dumps({
            "event": "control_termination",
            "task_id": self.task_id,
            "step": step_idx,
            "reason": self.termination_reason,
            "action": action,
        }))

    def build_summary(self) -> dict:
        """Build the control_summary dict from accumulated state."""
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "control_mode": self.config.get("controller_mode", "allow_or_terminate"),
            "router_mode": self.config.get("router_mode", "critical_only"),
            "include_visual_context": self.config.get("include_visual_context", True),
            "legibility_enabled": self.config.get("legibility_enabled", False),
            "review_count": self.review_count,
            "critical_count": self.critical_count,
            "blocked_count": self.blocked_count,
            "resample_count": self.resample_count,
            "resample_allowed_non_critical": self.resample_allowed_non_critical,
            "resample_allowed_after_review": self.resample_allowed_after_review,
            "resample_blocked_after_review": self.resample_blocked_after_review,
            "resample_failed": self.resample_failed,
            "trusted_fallback_count": self.trusted_fallback_count,
            "review_latency_ms_total": self.review_latency_ms_total,
            "terminated_by_control": self.terminated_by_control,
            "termination_reason": self.termination_reason,
        }

    def write_summary(self) -> None:
        """Write control_summary.json."""
        summary = self.build_summary()
        with open(self._summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        _logger.info(json.dumps({
            "event": "control_summary_written",
            "task_id": self.task_id,
            "review_count": summary["review_count"],
            "critical_count": summary["critical_count"],
            "blocked_count": summary["blocked_count"],
            "terminated": summary["terminated_by_control"],
        }))


def build_control_event(
    episode: dict,
    controller_decision: dict,
    final_action: str | None = None,
    final_action_source: str | None = None,
    resample_attempted: bool = False,
    resample_raw_response: str | None = None,
    resample_action: str | None = None,
    resample_reviewer_result: dict | None = None,
    trusted_fallback_attempted: bool = False,
    trusted_fallback_result: dict | None = None,
) -> dict:
    """Build a ControlEventLog dict from episode data and resolution metadata.

    One record per controller episode (original + any resample/fallback).
    """
    return {
        "task_id": episode["task_id"],
        "domain": episode["domain"],
        "step_index": episode["step_index"],
        "raw_action": episode["raw_action"],
        "normalized_action": episode["normalized_action"],
        "router_decision": episode["router_decision"],
        "legibility_report": episode.get("legibility_report"),
        "reviewer_result": episode.get("reviewer_result"),
        "review_latency_ms": episode.get("review_latency_ms"),
        "reviewer_model": episode.get("reviewer_model"),
        "resample_attempted": resample_attempted,
        "resample_raw_response": resample_raw_response,
        "resample_action": resample_action,
        "resample_reviewer_result": resample_reviewer_result,
        "trusted_fallback_attempted": trusted_fallback_attempted,
        "trusted_fallback_result": trusted_fallback_result,
        "final_action": final_action,
        "final_action_source": final_action_source,
        "controller_decision": controller_decision,
    }
