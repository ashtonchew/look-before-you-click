"""Rule-based critical-action router.

Answers one question: is this action important enough to review before
execution? Does NOT classify safety -- the reviewer does that.

Returns a RouterDecision dict. Never returns allow/block.
"""

import json
import logging
import re

from control.types import critical, not_critical, router_decision

_logger = logging.getLogger(__name__)
_loaded_router_config_cache = {}

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

# Matches string arguments inside write() / typewrite() calls in raw action text.
_WRITE_STRING_RE = re.compile(
    r"(?:write|typewrite)\s*\(\s*['\"]([^'\"]+)['\"]"
)

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
        "http://", "https://", "wget", "curl",
    ],
    "terminal_or_exec": [
        "terminal", "shell", "sudo", "install", "chmod", "run command",
        "executable", "rm", "rmdir", "mv",
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

# Keywords that are valid in typed text (shell/network commands).
# Checked against action["text"] separately from generic target-keyword
# matching to avoid email prose false positives.
_TYPED_COMMAND_FAMILIES: dict[str, list[str]] = {
    "terminal_or_exec": ["rm", "rmdir", "mv", "sudo", "chmod"],
    "external_navigation": ["wget", "curl"],
}


# ---- config loading ----

def _compile_family_patterns(
    family_keywords: dict[str, list[str]],
) -> dict[str, list[tuple[str, re.Pattern]]]:
    """Compile keyword lists into regex patterns.

    Pure-word keywords get \\b boundaries to prevent false positives
    (e.g. 'rm' matching 'form').  Keywords containing non-word chars
    at their boundaries (like 'http://') use plain substring matching
    since \\b doesn't apply cleanly to URL-like patterns.
    """
    compiled = {}
    for family, kws in family_keywords.items():
        patterns = []
        for kw in kws:
            escaped = re.escape(kw)
            if re.match(r'^\w', kw) and re.search(r'\w$', kw):
                pat = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
            else:
                pat = re.compile(escaped, re.IGNORECASE)
            patterns.append((kw, pat))
        compiled[family] = patterns
    return compiled


def _default_router_config() -> dict:
    """Return default router config values."""
    return {
        "family_keywords": FAMILY_KEYWORDS,
        "compiled_family_patterns": _compile_family_patterns(FAMILY_KEYWORDS),
        "secret_patterns": SECRET_PATTERNS,
        "dangerous_hotkeys": DANGEROUS_HOTKEYS,
    }


def _load_router_config(config: dict | None) -> dict:
    """Load router config overrides from config path."""
    path = (config or {}).get("critical_keywords_path")
    if not path:
        return _default_router_config()

    if path in _loaded_router_config_cache:
        return _loaded_router_config_cache[path]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        family_keywords = dict(FAMILY_KEYWORDS)
        if "family_keywords" in data:
            for family, kws in data["family_keywords"].items():
                family_keywords[family] = kws

        secret_patterns = SECRET_PATTERNS
        if "secret_patterns" in data:
            secret_patterns = [re.compile(pattern) for pattern in data["secret_patterns"]]

        dangerous_hotkeys = DANGEROUS_HOTKEYS
        if "dangerous_hotkeys" in data:
            dangerous_hotkeys = {
                frozenset(key.lower() for key in hotkey)
                for hotkey in data["dangerous_hotkeys"]
            }

        loaded = {
            "family_keywords": family_keywords,
            "compiled_family_patterns": _compile_family_patterns(family_keywords),
            "secret_patterns": secret_patterns,
            "dangerous_hotkeys": dangerous_hotkeys,
        }
        _loaded_router_config_cache[path] = loaded
        return loaded
    except Exception as e:
        _logger.warning(json.dumps({
            "event": "keyword_load_failed", "path": path, "error": str(e),
        }))
        return _default_router_config()


# ---- public API ----

def route(action: dict, config: dict) -> dict:
    """Decide whether an action is critical (needs review).

    Returns a RouterDecision dict.
    """
    special = action.get("special_token")
    router_config = _load_router_config(config)

    # Always-review mode: review everything except special tokens
    if config.get("router_mode") == "always":
        if special in ("WAIT", "DONE", "FAIL"):
            return not_critical()
        return router_decision(
            critical=True,
            reasons=["blanket review mode"],
            confidence=0.9,
        )

    # Special tokens are never critical
    if special in ("WAIT", "DONE", "FAIL"):
        return not_critical()

    # Secret-like text in type/hotkey actions
    kind = action.get("primary_kind", "")
    if kind in ("type", "hotkey", "press"):
        text = action.get("text") or ""
        if _looks_like_secret(text, config, router_config["secret_patterns"]):
            return critical("credential_or_secret_exposure",
                            "typed text matches secret pattern")

    # URL in typed text -> external navigation
    if kind in ("type", "hotkey") and _text_contains_url(action.get("text") or ""):
        return critical("external_navigation", "typed text contains URL")

    # URL in raw action (catches multi-call write+press patterns where the
    # normalizer picked a later call as last-impactful and lost the URL)
    if _raw_action_contains_url(action):
        return critical("external_navigation", "raw action contains URL")

    # Target UI element matches a critical keyword
    family, keyword = _check_target_keywords(action, router_config)
    if family:
        return critical(family, f"target text matches: {keyword}")

    # Shell/network commands in typed text (narrow keyword set only)
    family, keyword = _check_typed_commands(action)
    if family:
        return critical(family, f"typed command matches: {keyword}")

    # Terminal tag or dangerous hotkey
    if _is_terminal_or_dangerous_hotkey(action, router_config["dangerous_hotkeys"]):
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


def _looks_like_secret(
    text: str,
    config: dict = None,
    secret_patterns: list | None = None,
) -> bool:
    """Check if text matches any secret-like pattern.

    Email detection is conditional: skip if the task domain is email-related.
    """
    patterns = secret_patterns or SECRET_PATTERNS
    for pattern in patterns:
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


def _raw_action_contains_url(action: dict) -> bool:
    """Check if any write()/typewrite() call in the raw action contains a URL.

    Catches multi-call patterns like write(URL) + press('enter') where the
    normalizer picks press as last-impactful and loses the URL.
    """
    raw = action.get("raw_action", "")
    for m in _WRITE_STRING_RE.finditer(raw):
        if "http://" in m.group(1) or "https://" in m.group(1):
            return True
    return False


def _check_target_keywords(action: dict, router_config: dict | None = None) -> tuple[str | None, str | None]:
    """Check target name/text/tag and nearby_text against family keywords.

    Checks UI-element fields plus nearby_text (a11y proximity labels).
    Freeform typed text is excluded to avoid false positives from email
    prose containing words like "send" or "attached".

    Shell/network commands in typed text are handled by
    _check_typed_commands() instead.

    Returns (family, matched_keyword) or (None, None).
    """
    config = router_config or {}
    parts = []
    for field in ("target_name", "target_text", "target_tag", "nearby_text"):
        val = action.get(field)
        if val:
            parts.append(val.lower())
    combined = " ".join(parts)

    if not combined:
        return None, None

    compiled = config.get("compiled_family_patterns")
    if compiled is None:
        families = config.get("family_keywords") or FAMILY_KEYWORDS
        compiled = _compile_family_patterns(families)

    for family, patterns in compiled.items():
        for kw, pattern in patterns:
            if pattern.search(combined):
                return family, kw

    return None, None


def _check_typed_commands(action: dict) -> tuple[str | None, str | None]:
    """Check typed text for shell/network command keywords.

    Checks action["text"] on type actions, then falls back to scanning
    write()/typewrite() calls in the raw action string.  The fallback
    catches multi-call patterns (e.g. typewrite('rm -rf /') + press('enter'))
    where the normalizer picks 'press' as primary_kind and loses the
    typed text -- mirroring _raw_action_contains_url().

    Uses word-boundary matching against a narrow set of command keywords
    (rm, sudo, curl, etc.) to preserve recall for dangerous terminal
    commands without triggering on email prose.

    Returns (family, matched_keyword) or (None, None).
    """
    # Direct typed text
    if action.get("primary_kind") == "type":
        text = action.get("text") or ""
        if text:
            text_lower = text.lower()
            for family, keywords in _TYPED_COMMAND_FAMILIES.items():
                for kw in keywords:
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                        return family, kw

    # Raw-action fallback: scan write()/typewrite() call arguments
    raw = action.get("raw_action", "")
    for m in _WRITE_STRING_RE.finditer(raw):
        arg = m.group(1).lower()
        for family, keywords in _TYPED_COMMAND_FAMILIES.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', arg):
                    return family, kw

    return None, None


def _is_terminal_or_dangerous_hotkey(
    action: dict,
    dangerous_hotkeys: set | None = None,
) -> bool:
    """Check for terminal launch or dangerous hotkey combos."""
    kind = action.get("primary_kind", "")
    hotkeys = dangerous_hotkeys or DANGEROUS_HOTKEYS

    # Dangerous hotkey
    if kind == "hotkey":
        keys = action.get("keys") or []
        key_set = frozenset(k.lower() for k in keys)
        if key_set in hotkeys:
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
