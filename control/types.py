"""Type constructors for the control protocol.

All schemas match handoff_shared.md section 6 exactly.
Plain dicts throughout -- no dataclasses, no validation.
"""


def normalized_action(raw_action: str, primary_kind: str, **kwargs) -> dict:
    """Create a NormalizedAction dict with defaults.

    Does NOT include target_* fields -- those are merged later
    by a11y_parser.match_target() in the controller.
    """
    return {
        "raw_action": raw_action,
        "primary_kind": primary_kind,
        "x": kwargs.get("x"),
        "y": kwargs.get("y"),
        "text": kwargs.get("text"),
        "keys": kwargs.get("keys"),
        "button": kwargs.get("button"),
        "special_token": kwargs.get("special_token"),
    }


def router_decision(critical: bool, family: str | None = None,
                     reasons: list[str] | None = None,
                     confidence: float = 1.0) -> dict:
    """Create a RouterDecision dict."""
    return {
        "critical": critical,
        "family": family,
        "reasons": reasons or [],
        "confidence": confidence,
    }


def not_critical() -> dict:
    """Shorthand for a non-critical RouterDecision."""
    return router_decision(critical=False)


def critical(family: str, reason: str, confidence: float = 0.9) -> dict:
    """Shorthand for a critical RouterDecision."""
    return router_decision(
        critical=True, family=family, reasons=[reason], confidence=confidence,
    )


def no_target_match() -> dict:
    """Standard dict for when no a11y target is found."""
    return {
        "target_matched": False,
        "target_tag": None,
        "target_name": None,
        "target_text": None,
        "target_bounds": None,
        "target_match_method": "none",
    }


# ---- 4-way reviewer result ----

VALID_DECISIONS = {"ALLOW", "RESAMPLE", "DEFER_TO_TRUSTED", "BLOCK"}

MODE_ALLOWED_DECISIONS = {
    "allow_or_terminate": {"ALLOW", "BLOCK"},
    "allow_or_resample_once": {"ALLOW", "RESAMPLE", "BLOCK"},
    "allow_or_trusted_fallback_once": {"ALLOW", "DEFER_TO_TRUSTED", "BLOCK"},
}


def reviewer_result(decision: str, risk_score: float, primary_reason: str,
                    evidence: list[str],
                    safer_alternative: str | None = None) -> dict:
    """Create a ReviewerResult dict."""
    return {
        "decision": decision,
        "risk_score": risk_score,
        "primary_reason": primary_reason,
        "evidence": evidence,
        "safer_alternative": safer_alternative,
    }


def trusted_fallback_result(action: str | None, reason: str,
                            confidence: float) -> dict:
    """Create a TrustedFallbackResult dict."""
    return {
        "action": action,
        "reason": reason,
        "confidence": confidence,
    }


def controller_decision(
    execute: bool,
    was_critical: bool,
    termination_reason: str | None = None,
    reviewer_decision: str | None = None,
    action_to_execute: str | None = None,
    action_source: str | None = None,
    resample_requested: bool = False,
    trusted_fallback_requested: bool = False,
) -> dict:
    """Create a ControllerDecision dict."""
    return {
        "execute": execute,
        "termination_reason": termination_reason,
        "was_critical": was_critical,
        "reviewer_decision": reviewer_decision,
        "action_to_execute": action_to_execute,
        "action_source": action_source,
        "resample_requested": resample_requested,
        "trusted_fallback_requested": trusted_fallback_requested,
    }


def control_event_log(
    task_id: str,
    domain: str,
    step_index: int,
    raw_action: str,
    normalized_action: dict,
    router_decision: dict,
    controller_decision: dict,
    legibility_report: dict | None = None,
    reviewer_result: dict | None = None,
    review_latency_ms: int | None = None,
    reviewer_model: str | None = None,
    resample_attempted: bool = False,
    resample_raw_response: str | None = None,
    resample_action: str | None = None,
    resample_reviewer_result: dict | None = None,
    trusted_fallback_attempted: bool = False,
    trusted_fallback_result: dict | None = None,
    final_action: str | None = None,
    final_action_source: str | None = None,
) -> dict:
    """Create a ControlEventLog dict -- one per controller episode."""
    return {
        "task_id": task_id,
        "domain": domain,
        "step_index": step_index,
        "raw_action": raw_action,
        "normalized_action": normalized_action,
        "router_decision": router_decision,
        "legibility_report": legibility_report,
        "reviewer_result": reviewer_result,
        "review_latency_ms": review_latency_ms,
        "reviewer_model": reviewer_model,
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


def review_episode(
    task_id: str,
    domain: str,
    step_index: int,
    raw_action: str,
    normalized_action: dict,
    router_decision: dict,
    action_source: str = "untrusted",
    legibility_report: dict | None = None,
    reviewer_result: dict | None = None,
    review_latency_ms: int | None = None,
    reviewer_model: str | None = None,
    review_package_path: str | None = None,
) -> dict:
    """Create a ReviewEpisode dict."""
    return {
        "task_id": task_id,
        "domain": domain,
        "step_index": step_index,
        "raw_action": raw_action,
        "normalized_action": normalized_action,
        "router_decision": router_decision,
        "legibility_report": legibility_report,
        "reviewer_result": reviewer_result,
        "review_latency_ms": review_latency_ms,
        "reviewer_model": reviewer_model,
        "review_package_path": review_package_path,
        "action_source": action_source,
    }
