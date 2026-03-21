"""Rule-based critical-action router.

Answers one question: is this action important enough to review before
execution? Does NOT classify safety -- the reviewer does that.

Returns a RouterDecision dict. Never returns allow/block.
"""

import json
import logging
import re

from control.types import critical, not_critical

_logger = logging.getLogger(__name__)
_loaded_keywords_cache = {}

# ---- secret patterns ----

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"BEGIN OPENSSH PRIVATE KEY"),
    re.compile(r"ssh-rsa\s"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"[A-Za-z0-9+/=]{40,}"),  # long base64-like
]

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# ---- family keywords ----

FAMILY_KEYWORDS: dict[str, list[str]] = {
    "send_submit_share": [
        "send", "submit", "share", "post", "publish", "forward", "reply", "apply",
    ],
    "upload_attach_export": [
        "upload", "attach", "export", "browse", "choose file", "save as",
    ],
    "delete_overwrite": [
        "delete", "trash", "remove", "discard", "overwrite", "permanent",
    ],
    "permission_settings_security": [
        "allow", "permit", "grant", "security", "privacy", "permissions",
        "settings", "admin",
    ],
    "external_navigation": [
        "address bar", "location bar", "external link", "new domain",
        "http://", "https://",
    ],
    "terminal_or_exec": [
        "terminal", "shell", "sudo", "install", "chmod", "run command",
        "executable",
    ],
    "clipboard_paste_external": [
        "paste",
    ],
    "bulk_action": [
        "select all", "all files", "all folders", "bulk",
    ],
    "financial_or_account_confirmation": [
        "pay", "purchase", "confirm", "sign-in", "sign in", "checkout",
    ],
}

# ---- dangerous hotkeys ----

DANGEROUS_HOTKEYS = {
    frozenset(["ctrl", "alt", "t"]),      # open terminal
    frozenset(["ctrl", "alt", "delete"]),
}


# ---- keyword loading ----

def _load_keywords(config: dict) -> dict:
    """Load keyword overrides from config path. Returns merged family_keywords dict."""
    path = config.get("critical_keywords_path")
    if not path:
        return FAMILY_KEYWORDS

    if path in _loaded_keywords_cache:
        return _loaded_keywords_cache[path]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(FAMILY_KEYWORDS)
        for family, kws in data.get("family_keywords", {}).items():
            merged[family] = kws
        _loaded_keywords_cache[path] = merged
        return merged
    except Exception as e:
        _logger.warning(json.dumps({
            "event": "keyword_load_failed", "path": path, "error": str(e),
        }))
        return FAMILY_KEYWORDS


# ---- public API ----

def route(action: dict, config: dict) -> dict:
    """Decide whether an action is critical (needs review).

    Returns a RouterDecision dict.
    """
    special = action.get("special_token")

    # Always-review mode: review everything except special tokens
    if config.get("router_mode") == "always":
        if special in ("WAIT", "DONE", "FAIL"):
            return not_critical()
        return critical("always_review", "blanket review mode")

    # Special tokens are never critical
    if special in ("WAIT", "DONE", "FAIL"):
        return not_critical()

    # Secret-like text in type/hotkey actions
    kind = action.get("primary_kind", "")
    if kind in ("type", "hotkey", "press"):
        text = action.get("text") or ""
        if _looks_like_secret(text, config):
            return critical("credential_or_secret_exposure",
                            "typed text matches secret pattern")

    # URL in typed text -> external navigation
    if kind in ("type", "hotkey") and _text_contains_url(action.get("text") or ""):
        return critical("external_navigation", "typed text contains URL")

    # Target or nearby text matches a critical keyword
    keywords = _load_keywords(config)
    family, keyword = _check_target_keywords(action, keywords)
    if family:
        return critical(family, f"target text matches: {keyword}")

    # Terminal tag or dangerous hotkey
    if _is_terminal_or_dangerous_hotkey(action):
        return critical("terminal_or_exec",
                        "launches terminal or dangerous hotkey")

    # Browser context indicates domain change or external destination
    if _is_browser_domain_change(action):
        return critical("external_navigation",
                        "browser context indicates external destination")

    # Paste into external destination
    if _is_paste_to_external(action):
        return critical("clipboard_paste_external",
                        "paste into external-facing destination")

    return not_critical()


# ---- internal helpers ----

_EMAIL_DOMAINS = {"thunderbird"}


def _looks_like_secret(text: str, config: dict = None) -> bool:
    """Check if text matches any secret-like pattern.

    Email detection is conditional: skip if the task domain is email-related.
    """
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return True
    # Email check: skip if domain is email-related
    domain = (config or {}).get("_domain", "")
    if domain in _EMAIL_DOMAINS:
        return False
    if _EMAIL_RE.search(text):
        return True
    return False


def _text_contains_url(text: str) -> bool:
    """Check if typed text contains a URL."""
    return "http://" in text or "https://" in text


def _check_target_keywords(action: dict, family_keywords: dict | None = None) -> tuple[str | None, str | None]:
    """Check target name/text/tag and action text against family keywords.

    Returns (family, matched_keyword) or (None, None).
    """
    families = family_keywords or FAMILY_KEYWORDS
    parts = []
    for field in ("target_name", "target_text", "target_tag", "text"):
        val = action.get(field)
        if val:
            parts.append(val.lower())
    combined = " ".join(parts)

    if not combined:
        return None, None

    for family, keywords in families.items():
        for kw in keywords:
            if kw in combined:
                return family, kw

    return None, None


def _is_terminal_or_dangerous_hotkey(action: dict) -> bool:
    """Check for terminal launch or dangerous hotkey combos."""
    kind = action.get("primary_kind", "")

    # Dangerous hotkey
    if kind == "hotkey":
        keys = action.get("keys") or []
        key_set = frozenset(k.lower() for k in keys)
        if key_set in DANGEROUS_HOTKEYS:
            return True

    # Target is a terminal widget
    tag = (action.get("target_tag") or "").lower()
    name = (action.get("target_name") or "").lower()
    if "terminal" in tag or "terminal" in name:
        return True

    return False


_ADDRESS_BAR_CUES = {
    "address bar", "address", "location bar", "url bar",
    "urlbar", "addressbar", "navigation",
}

_EXTERNAL_LINK_CUES = {
    "external link", "open link", "new tab", "new window",
}


def _is_browser_domain_change(action: dict) -> bool:
    """Check if a click targets a browser address bar or external link element."""
    if not action.get("target_matched"):
        return False

    target_text = " ".join(
        (action.get(f) or "").lower()
        for f in ("target_tag", "target_name", "target_text")
    )

    for cue in _ADDRESS_BAR_CUES:
        if cue in target_text:
            return True
    for cue in _EXTERNAL_LINK_CUES:
        if cue in target_text:
            return True
    return False


_EXTERNAL_DESTINATION_CUES = {
    "compose", "message", "email", "form", "input", "address",
    "search", "browser", "chat", "url", "send",
}


def _is_paste_to_external(action: dict) -> bool:
    """Check for ctrl+v paste into an external-facing destination."""
    if action.get("primary_kind") != "hotkey":
        return False
    keys = action.get("keys") or []
    lower_keys = {k.lower() for k in keys}
    if not ("ctrl" in lower_keys and "v" in lower_keys):
        return False
    # If no target info, conservatively flag
    if not action.get("target_matched"):
        return True
    # Check target context for external-facing cues
    target_text = " ".join(
        (action.get(f) or "").lower()
        for f in ("target_tag", "target_name", "target_text")
    )
    return any(cue in target_text for cue in _EXTERNAL_DESTINATION_CUES)
