"""Controller orchestrator: normalize -> route -> review -> policy."""

import logging as _stdlib_logging
import json
import time

_logger = _stdlib_logging.getLogger("desktopenv.control")

from control.action_normalizer import normalize
from control.a11y_parser import parse_tree, match_target
from control.critical_router import route
from control.reviewer import generate_legibility, review as reviewer_review
from control.types import no_target_match

# For linearizing a11y tree in review packages
try:
    from mm_agents.agent import linearize_accessibility_tree as _linearize_tree
except ImportError:
    def _linearize_tree(raw):
        return str(raw) if raw else ""


# ---- module-level logger ----
# Set by lib_run_single.py before the action loop via set_logger().
_current_logger = None


def set_logger(logger):
    """Set the control logger for the current run. Call before review()."""
    global _current_logger
    _current_logger = logger


def review(
    instruction: str,
    obs: dict,
    raw_response: str,
    raw_action: str,
    recent_history: list[dict],
    step_idx: int,
    task_id: str,
    domain: str,
    config: dict,
) -> dict:
    """Orchestrate the control protocol for one action.

    Returns ControllerDecision:
        execute: bool
        termination_reason: str | None
        was_critical: bool  -- required by runtime handoff for recent_history tracking
    """
    # 0. Fast path: control disabled
    if not config.get("enabled", False):
        return {"execute": True, "termination_reason": None, "was_critical": False}

    # 1. Normalize action
    try:
        normalized = normalize(raw_action)
    except Exception as e:
        _logger.error(json.dumps({
            "event": "action_parse_error",
            "task_id": task_id,
            "step": step_idx,
            "error": str(e),
        }))
        return {"execute": False, "termination_reason": "unparsable_action", "was_critical": False}

    # 2. Parse a11y and match target (click-like actions with coordinates only)
    a11y_raw = obs.get("accessibility_tree", "")
    a11y_linearized = ""
    if a11y_raw:
        try:
            a11y_linearized = _linearize_tree(a11y_raw)
        except Exception as e:
            _logger.warning(json.dumps({
                "event": "a11y_linearize_error",
                "task_id": task_id,
                "step": step_idx,
                "error": str(e),
            }))

    if a11y_linearized and normalized.get("x") is not None:
        try:
            nodes = parse_tree(a11y_linearized)
            target_fields = match_target(nodes, normalized["x"], normalized["y"])
            normalized.update(target_fields)
        except Exception as e:
            _logger.warning(json.dumps({
                "event": "a11y_parse_error",
                "task_id": task_id,
                "step": step_idx,
                "error": str(e),
            }))
            normalized.update(no_target_match())

    # Ensure target_* fields exist even when a11y was skipped
    if "target_matched" not in normalized:
        normalized.update(no_target_match())

    # 3. Route (inject domain for context-aware routing)
    config["_domain"] = domain
    router_decision = route(normalized, config)
    config.pop("_domain", None)

    is_critical = router_decision["critical"]

    # 4. If not critical, allow immediately (no event logged)
    if not is_critical:
        return {"execute": True, "termination_reason": None, "was_critical": False}

    # 5. Legibility (critical only, optional)
    legibility_report = None
    if config.get("legibility_enabled"):
        try:
            legibility_report = generate_legibility(
                instruction, obs, raw_response, normalized, recent_history, config
            )
        except Exception as e:
            _logger.warning(json.dumps({
                "event": "legibility_error",
                "task_id": task_id,
                "step": step_idx,
                "error": str(e),
            }))

    # 6. Build review package
    package = {
        "instruction": instruction,
        "raw_response": raw_response,
        "normalized_action": normalized,
        "router_decision": router_decision,
        "obs": obs,
        "a11y_tree_linearized": a11y_linearized,
        "legibility_report": legibility_report,
        "recent_history": recent_history,
        "step_index": step_idx,
        "task_id": task_id,
        "domain": domain,
    }

    # 7. Save review package
    if _current_logger:
        _current_logger.save_review_package(package, step_idx)

    # 8. Trusted review
    reviewer_result = None
    review_latency_ms = None
    reviewer_model = config.get("reviewer_model", "gpt-4o")

    try:
        t0 = time.time()
        reviewer_result = reviewer_review(package, config)
        review_latency_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        _logger.error(json.dumps({
            "event": "review_error",
            "task_id": task_id,
            "step": step_idx,
            "error": str(e),
        }))
        if config.get("fail_closed_on_review_error", True):
            decision = {"execute": False, "termination_reason": "review_error_fail_closed", "was_critical": True}
            event = _build_event(
                task_id, domain, step_idx, raw_action, normalized,
                router_decision, legibility_report, None,
                decision, review_latency_ms=None, reviewer_model=reviewer_model,
            )
            if _current_logger:
                _current_logger.log_event(event)
            return decision
        raise

    # 9. Apply policy
    if reviewer_result["allow"] is True:
        decision = {"execute": True, "termination_reason": None, "was_critical": True}
    else:
        decision = {"execute": False, "termination_reason": reviewer_result["primary_reason"], "was_critical": True}

    # 10. Log event
    event = _build_event(
        task_id, domain, step_idx, raw_action, normalized,
        router_decision, legibility_report, reviewer_result,
        decision, review_latency_ms=review_latency_ms, reviewer_model=reviewer_model,
    )
    if _current_logger:
        _current_logger.log_event(event)

    return decision


def _build_event(
    task_id, domain, step_idx, raw_action, normalized,
    router_decision, legibility_report, reviewer_result,
    controller_decision, review_latency_ms, reviewer_model,
) -> dict:
    """Build a ControlEventLog dict."""
    return {
        "task_id": task_id,
        "domain": domain,
        "step_index": step_idx,
        "raw_action": raw_action,
        "normalized_action": normalized,
        "router_decision": router_decision,
        "legibility_report": legibility_report,
        "reviewer_result": reviewer_result,
        "controller_decision": controller_decision,
        "review_latency_ms": review_latency_ms,
        "reviewer_model": reviewer_model,
    }
