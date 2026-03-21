"""Normalize raw pyautogui action strings into NormalizedAction dicts.

Regex-based parsing only -- no ast or real Python parser.
Handles: click, doubleClick, rightClick, moveTo, dragTo, write,
typewrite, press, hotkey, scroll, and special tokens WAIT/DONE/FAIL.
"""

import logging
import re

from control.types import normalized_action

logger = logging.getLogger(__name__)

# Supported pyautogui methods
_METHODS = (
    "click", "doubleClick", "rightClick", "moveTo", "dragTo",
    "write", "typewrite", "press", "hotkey", "scroll",
)

_METHOD_PATTERN = re.compile(
    r"pyautogui\.(" + "|".join(_METHODS) + r")\s*\(",
)

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_KWARG = re.compile(r"(\w+)\s*=\s*")
_QUOTED = re.compile(r"""(['"])(.*?)\1""")


# ---- public API ----

def normalize(raw_action: str) -> dict:
    """Parse a raw pyautogui action string into a NormalizedAction dict.

    Returns NormalizedAction *without* target_* fields populated --
    those are merged later by a11y_parser.match_target().
    """
    stripped = raw_action.strip()

    # 1. Special tokens
    if stripped in ("WAIT", "DONE", "FAIL"):
        kind = stripped.lower()
        return normalized_action(raw_action, kind, special_token=stripped)

    # 2. Extract pyautogui calls
    calls = _extract_calls(raw_action)
    if not calls:
        raise ValueError(f"no pyautogui calls found in action: {raw_action[:200]}")

    # 3. Pick last impactful primitive, inherit coords from moveTo
    return _pick_last_impactful(raw_action, calls)


# ---- internal helpers ----

def _extract_calls(raw: str) -> list[tuple[str, str]]:
    """Find all pyautogui.method(...) calls and return (method, args_str) pairs."""
    results = []
    for m in _METHOD_PATTERN.finditer(raw):
        method = m.group(1)
        start = m.end()  # position right after the '('
        args_str = _find_matching_paren(raw, start)
        if args_str is not None:
            results.append((method, args_str))
    return results


def _find_matching_paren(text: str, start: int) -> str | None:
    """Extract content between the already-consumed '(' and its matching ')'.

    Handles nested parens and quoted strings.
    """
    depth = 1
    i = start
    in_quote = None
    while i < len(text) and depth > 0:
        ch = text[i]
        if in_quote:
            if ch == in_quote and (i == 0 or text[i - 1] != "\\"):
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[start:i - 1]


def _parse_args(args_str: str) -> dict:
    """Parse positional and keyword arguments from an args string.

    Returns dict with keys: positional (list), and any keyword args.
    """
    result: dict = {"_positional": []}
    remaining = args_str.strip()
    if not remaining:
        return result

    # Tokenize: split by commas, but respect quotes and parens
    tokens = _split_args(remaining)
    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Check for keyword arg
        kw_match = _KWARG.match(token)
        if kw_match:
            key = kw_match.group(1)
            val = token[kw_match.end():].strip()
            result[key] = _parse_value(val)
        else:
            result["_positional"].append(_parse_value(token))

    return result


def _split_args(s: str) -> list[str]:
    """Split argument string by commas, respecting quotes and parens."""
    parts = []
    current = []
    depth = 0
    in_quote = None
    for ch in s:
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
            current.append(ch)
        elif ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _parse_value(val: str):
    """Parse a single value: number, quoted string, or raw string."""
    val = val.strip()
    # Quoted string
    q = _QUOTED.fullmatch(val)
    if q:
        return q.group(2)
    # Number
    n = _NUMBER.fullmatch(val)
    if n:
        f = float(val)
        return int(f) if f == int(f) else f
    # Bracketed list like ['a', 'b']
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        return [_parse_value(v) for v in _split_args(inner)]
    # Raw identifier or expression
    return val


def _resolve_call(method: str, args: dict, raw_action: str) -> dict:
    """Convert a single pyautogui call into a NormalizedAction dict."""
    pos = args.get("_positional", [])

    if method in ("click", "doubleClick", "rightClick"):
        kind_map = {
            "click": "click",
            "doubleClick": "double_click",
            "rightClick": "right_click",
        }
        x = args.get("x", pos[0] if len(pos) >= 1 and isinstance(pos[0], (int, float)) else None)
        y = args.get("y", pos[1] if len(pos) >= 2 and isinstance(pos[1], (int, float)) else None)
        button = args.get("button")
        if isinstance(button, str):
            button = button
        return normalized_action(raw_action, kind_map[method], x=x, y=y, button=button)

    if method == "moveTo":
        x = args.get("x", pos[0] if len(pos) >= 1 and isinstance(pos[0], (int, float)) else None)
        y = args.get("y", pos[1] if len(pos) >= 2 and isinstance(pos[1], (int, float)) else None)
        return normalized_action(raw_action, "move", x=x, y=y)

    if method == "dragTo":
        x = args.get("x", pos[0] if len(pos) >= 1 and isinstance(pos[0], (int, float)) else None)
        y = args.get("y", pos[1] if len(pos) >= 2 and isinstance(pos[1], (int, float)) else None)
        return normalized_action(raw_action, "drag", x=x, y=y)

    if method in ("write", "typewrite"):
        text = pos[0] if pos and isinstance(pos[0], str) else args.get("message", args.get("text"))
        return normalized_action(raw_action, "type", text=text)

    if method == "press":
        key = pos[0] if pos else args.get("keys")
        keys = key if isinstance(key, list) else [key] if key else []
        return normalized_action(raw_action, "press", keys=keys)

    if method == "hotkey":
        keys = [p for p in pos if isinstance(p, str)]
        return normalized_action(raw_action, "hotkey", keys=keys)

    if method == "scroll":
        amount = pos[0] if pos and isinstance(pos[0], (int, float)) else None
        return normalized_action(raw_action, "scroll", text=str(amount) if amount is not None else None)

    return normalized_action(raw_action, "other")


def _pick_last_impactful(raw_action: str, calls: list[tuple[str, str]]) -> dict:
    """Pick the last impactful call. Inherit coords from preceding moveTo."""
    last_move_x = None
    last_move_y = None
    last_impactful = None

    for method, args_str in calls:
        args = _parse_args(args_str)
        resolved = _resolve_call(method, args, raw_action)

        if method == "moveTo":
            last_move_x = resolved.get("x")
            last_move_y = resolved.get("y")
        else:
            last_impactful = resolved

    if last_impactful is None:
        # Only moveTo calls -- treat the last moveTo as the action
        if last_move_x is not None:
            return normalized_action(raw_action, "other", x=last_move_x, y=last_move_y)
        return normalized_action(raw_action, "other")

    # Inherit coords from moveTo if the impactful call has none
    if last_impactful.get("x") is None and last_move_x is not None:
        if last_impactful["primary_kind"] in ("click", "double_click", "right_click"):
            last_impactful["x"] = last_move_x
            last_impactful["y"] = last_move_y

    return last_impactful
