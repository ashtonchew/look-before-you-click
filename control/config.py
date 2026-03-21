"""Load and merge control protocol configuration."""

import json


def load_control_config(path: str | None) -> dict | None:
    """Load control config from a JSON file.

    Returns None if path is None (control disabled).
    Raises on file-not-found or invalid JSON.
    """
    if path is None:
        return None

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    _REQUIRED_KEYS = {
        "enabled", "router_mode", "controller_mode",
        "include_visual_context", "legibility_enabled",
        "fail_closed_on_review_error", "critical_keywords_path",
    }
    missing = _REQUIRED_KEYS - set(config.keys())
    if missing:
        raise ValueError(
            f"Control config at {path} missing required keys: {sorted(missing)}"
        )

    return config


def merge_cli_overrides(
    config: dict,
    control_mode: str | None = None,
    reviewer_model: str | None = None,
    legibility_model: str | None = None,
) -> dict:
    """Merge CLI flag overrides into the loaded config dict.

    Mutates and returns config.
    """
    if control_mode is not None:
        config["controller_mode"] = control_mode
    if reviewer_model is not None:
        config["reviewer_model"] = reviewer_model
    if legibility_model is not None:
        config["legibility_model"] = legibility_model
    return config
