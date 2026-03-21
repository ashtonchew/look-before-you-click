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
