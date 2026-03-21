# Shared Context — All Agents Read First

**Status:** authoritative for implementation (supersedes `data_types.md`, `architecture.md`, `workstreams.md`)
**Source:** extracted from `docs/technical_spec.md` sections 1, 3.6–3.10, 4, 5.2, 7.2–7.3, 8, 24, 27

---

## 1. Engineering Principles

### Code style
- Write code that is easy to skim.
- Prefer short files and short functions.
- Use obvious names and early returns.
- Avoid inheritance unless it removes duplicated code right now.
- Avoid "frameworks" inside the repo.
- Avoid clever abstractions. Keep state explicit.
- Prefer plain dicts / dataclasses / typed functions over meta-programming.
- Log in structured JSON whenever possible.
- If a piece of code feels "smart", simplify it.

### Scope control
Do **not** build: a new benchmark, a new agent architecture, training pipelines, OCR pipelines, world models, async services, a database, a message queue, a browser extension, a system-level isolation framework, a fancy dashboard, protocol-aware attacker scaffolds, custom training, GUI world models, new task generation, LinuxArena integration, browser extension instrumentation, fancy statistical tests, or an interactive dashboard.

### Product rule
The deliverable is **a protocol wrapper plus evaluation**, not a new agent. Start from OS-Harm, keep the existing agent path intact, intercept actions before execution, add review only where needed, log everything cleanly, compute the safety/usefulness tradeoff.

### Paper-honesty guardrails
1. **Keep B2 or drop the "sparse beats blanket" claim.** Run B2 on a small slice (3–5 tasks) as supporting evidence. If compute doesn't allow even that, weaken the paper framing.
2. **Don't call the MVP "deferral" until deferral exists.** The MVP implements ALLOW / BLOCK only. Call it "critical-action routing with state-grounded review."

---

## 2. Key Design Decisions

These are settled. Do not revisit.

| Decision | Choice | Rationale |
|---|---|---|
| Router | Rule-based in MVP, no LLM router | Easier to debug, explain, cheaper |
| Reviewer | Separate trusted call, critical actions only | Do not monitor every step |
| Legibility | Separate function inside `reviewer.py`, do not change base agent prompt | Keeps base agent stable |
| Controller default | `allow_or_terminate` | Simplest semantics |
| Judge | Explicit post-run call always | Current `run.py` has judgment block commented out |

---

## 3. Architecture

```text
run.py
  └── lib_run_single.run_single_example(...)
        ├── agent.predict(instruction, obs)          # UNTOUCHED
        ├── control.controller.review(...)           # OUR LAYER
        │     ├── action_normalizer    → pyautogui string to NormalizedAction
        │     ├── a11y_parser          → linearized tree to node list + target match
        │     ├── critical_router      → rule-based: is this action critical?
        │     ├── reviewer             → legibility + trusted review (critical only)
        │     └── controller_policy    → allow / terminate
        ├── env.step(...)                            # UNTOUCHED
        ├── OS-Harm logging                          # UNTOUCHED
        ├── control logging                          # NEW
        └── explicit post-run judge call             # NEW
```

---

## 4. Authoritative File Layout

This layout supersedes `architecture.md`. Do not create files not listed here.

### Patch (minimal changes only)
- `run.py` — CLI flags, wire control config
- `lib_run_single.py` — controller hook between predict and step

### New: `control/`
| File | Owner | Purpose |
|---|---|---|
| `__init__.py` | WS1 | Package init (keep minimal) |
| `config.py` | WS1 | Load JSON control config, return dict |
| `controller.py` | WS1 | Orchestrator: calls normalizer → router → reviewer → policy |
| `logging.py` | WS1 | Write `control_events.jsonl` + `control_summary.json` + save review packages |
| `judge_adapter.py` | WS1 | Normalize judge output |
| `types.py` | WS2 | All data type definitions |
| `action_normalizer.py` | WS2 | pyautogui string → NormalizedAction |
| `a11y_parser.py` | WS2 | Tree parsing + click target matching |
| `critical_router.py` | WS2 | Rule-based router |
| `reviewer.py` | WS2 | Trusted reviewer + legibility function (one file) |
| `prompts.py` | WS2 | ALL prompt templates (single source of truth) |

### New: `analysis/`
| File | Owner | Purpose |
|---|---|---|
| `__init__.py` | WS3 | Package init |
| `aggregate.py` | WS3 | Run folders → `results_summary.csv` + frontier plot. Split only if >300 lines |

### New: `configs/`
| File | Owner | Baseline |
|---|---|---|
| `control_none.json` | WS3 | B0 — no control |
| `control_always_review_language_only.json` | WS3 | B1 — blanket monitor, language-only |
| `control_always_review_state_grounded.json` | WS3 | B2 — blanket monitor, state-grounded (small slice) |
| `control_critical.json` | WS3 | B3 — rule-based routing, no legibility |
| `control_critical_legibility.json` | WS3 | B4 — routing + legibility |

---

## 5. Discrepancy Resolution

The following standalone docs are **stale**. Where they conflict with this document, this document wins.

| Issue | Stale doc says | Authoritative (this doc) |
|---|---|---|
| `ObservationSnapshot` type | `data_types.md` defines it | Removed — pass raw `obs` dict directly |
| `TrustedFacts` type | `data_types.md` defines it | Deferred entirely — do not implement |
| `A11yTarget` type | `data_types.md` defines separately | Merged into `NormalizedAction` as `target_*` fields |
| `NormalizedAction.sub_actions` | `data_types.md` includes it | Removed — extract last impactful primitive only |
| `NormalizedAction.raw_format` | `data_types.md` has `"pyautogui" \| "computer_13"` | Removed — pyautogui only |
| `ControllerDecision.action_to_execute` | `data_types.md` includes it | Removed for MVP — add only for stretch modes |
| `fact_extractor.py` | `architecture.md` lists it | Deferred — do not create this file |
| `legibility.py` as separate file | `architecture.md` lists it | One function inside `reviewer.py` |
| `trusted_reviewer.py` as separate file | `architecture.md` lists it | Merged into `reviewer.py` |
| `log_io.py` + `metrics.py` | `architecture.md` lists separately | Merged into `logging.py` |
| 4-agent workstream split | `workstreams.md` defines A–D | 3 workstreams (this doc) |
| `action_to_execute` in §6.2 pseudocode | Tech spec §6.2 uses it | Internal inconsistency — removed per §8.7. When `execute=True`, runtime passes original `raw_action` to `env.step()` |

---

## 6. Data Model — All Type Schemas

These are the single source of truth. WS2 implements them in `types.py`. All workstreams reference them.

### NormalizedAction
```python
NormalizedAction = {
  "raw_action": str,
  "primary_kind": "click" | "double_click" | "right_click" | "type" | "press" |
                  "hotkey" | "scroll" | "drag" | "wait" | "done" | "fail" | "other",
  "x": float | None,
  "y": float | None,
  "text": str | None,
  "keys": list[str] | None,
  "button": str | None,
  "special_token": "WAIT" | "DONE" | "FAIL" | None,
  # Target info (merged from a11y matching)
  "target_matched": bool,
  "target_tag": str | None,
  "target_name": str | None,
  "target_text": str | None,
  "target_bounds": {"x": float, "y": float, "w": float, "h": float} | None,
  "target_match_method": "contains_point" | "nearest_center" | "none"
}
```

### RouterDecision
```python
RouterDecision = {
  "critical": bool,
  "family": str | None,
  "reasons": list[str],
  "confidence": float
}
```

### LegibilityReport
Generated only for critical actions if legibility is enabled.
```python
LegibilityReport = {
  "action_type": str,
  "target_element": str,
  "target_text_or_label": str,
  "why_needed_for_user_goal": str,
  "expected_visible_effect_next": str,
  "what_could_go_wrong": str,
  "security_relevance": "low" | "medium" | "high",
  "confidence": float
}
```

### ReviewPackage
```python
ReviewPackage = {
  "instruction": str,
  "raw_response": str,
  "normalized_action": NormalizedAction,
  "router_decision": RouterDecision,
  "obs": dict,                    # OSWorld obs dict passed directly (screenshot + a11y_tree)
  "a11y_tree_linearized": str,
  "legibility_report": LegibilityReport | None,
  "recent_history": list[dict],
  "step_index": int,
  "task_id": str,
  "domain": str
}
```

### ReviewerResult
```python
ReviewerResult = {
  "allow": bool,
  "risk_score": float,
  "primary_reason": str,
  "evidence": list[str],
  "safer_alternative": str | None
}
```

### ControllerDecision
```python
ControllerDecision = {
  "execute": bool,
  "termination_reason": str | None
}
```
Stretch modes will add `resample_requested` and `trusted_fallback_requested` fields when implemented.

### ControlEventLog
One JSONL record per reviewed action.
```python
ControlEventLog = {
  "task_id": str,
  "domain": str,
  "step_index": int,
  "raw_action": str,
  "normalized_action": dict,
  "router_decision": dict,
  "legibility_report": dict | None,
  "reviewer_result": dict | None,
  "controller_decision": dict,
  "review_latency_ms": int | None,
  "reviewer_model": str | None
}
```

---

## 7. Integration Contract

These are the exact function signatures at the seam between WS1 and WS2.

### Top-level entry point (WS1 calls from `lib_run_single.py`)
```python
# control/controller.py — owned by WS1
def review(
    instruction: str,
    obs: dict,                    # raw OSWorld obs (screenshot + a11y_tree)
    raw_response: str,
    raw_action: str,
    recent_history: list[dict],
    step_idx: int,
    task_id: str,
    domain: str,
    config: dict
) -> ControllerDecision:
    ...
```

### WS2 exports (called by WS1's `controller.py`)
```python
# control/action_normalizer.py
def normalize(raw_action: str) -> dict:
    """Returns NormalizedAction dict (without target_* fields)."""

# control/a11y_parser.py
def parse_tree(a11y_tree_raw: str) -> list[dict]:
    """Returns list of A11yNode dicts with tag, name, text, class, description, x, y, w, h."""

def match_target(nodes: list[dict], x: float, y: float) -> dict:
    """Returns target_* fields to merge into NormalizedAction."""

# control/critical_router.py
def route(action: dict, config: dict) -> dict:
    """Takes NormalizedAction (with target), returns RouterDecision."""

# control/reviewer.py
def generate_legibility(
    instruction: str,
    obs: dict,
    raw_response: str,
    action: dict,
    recent_history: list[dict],
    config: dict
) -> dict | None:
    """Returns LegibilityReport or None on failure. Never raises."""

def review(package: dict, config: dict) -> dict:
    """Takes ReviewPackage, returns ReviewerResult. Raises on error (fail closed)."""
```

---

## 8. Config Schema

Both WS1 (loads at runtime) and WS3 (defines JSON files) must follow this schema.

```json
{
  "enabled": true,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": true,
  "legibility_enabled": true,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

### Baseline mode mapping
| Mode name | Config key | `router_mode` | `include_visual_context` | `legibility_enabled` |
|---|---|---|---|---|
| B0 — none | `control_none.json` | n/a (`enabled: false`) | n/a | n/a |
| B1 — always_review_language_only | `control_always_review_language_only.json` | `"always"` | `false` | `false` |
| B2 — always_review_state_grounded | `control_always_review_state_grounded.json` | `"always"` | `true` | `false` |
| B3 — critical_review | `control_critical.json` | `"critical_only"` | `true` | `false` |
| B4 — critical_review_legibility | `control_critical_legibility.json` | `"critical_only"` | `true` | `true` |

---

## 9. Failure Handling Rules

These are strict. Do not improvise alternatives.

| Failure | Action | Terminate? |
|---|---|---|
| Review model errors on critical action | Fail closed, log `review_error_fail_closed` | Yes |
| Legibility call fails | Continue with `legibility_report = None`, log error | No |
| A11y parsing fails | Continue with raw a11y text, set target = None | No |
| Judge fails after run | Mark judge output missing, keep run output | No |
| Agent outputs unparsable action | Log parse error | Yes |

Never silently recover or "fix" broken output. Be loud about errors.

---

## 10. Coding Conventions

### Function shape
```python
def route_action(action, target, facts):
    if action["special_token"] in {"WAIT", "DONE", "FAIL"}:
        return {"critical": False, "family": None, "reasons": [], "confidence": 1.0}

    if looks_like_secret_exposure(action):
        return critical("credential_or_secret_exposure", "typed text looks like a secret")

    if target and target_contains_send_word(target):
        return critical("send_submit_share", "target element looks like send/submit/share")

    return not_critical()
```

### Logging shape
```python
# Good:
logger.info(json.dumps({"event": "review_disallowed", "task_id": task_id, "step": step_idx}))

# Bad:
logger.info(f"Something suspicious happened maybe around step {step_idx}")
```

### Other rules
- Keep files under ~300 lines unless there is a good reason.
- Store all prompts in `control/prompts.py`. Do not inline giant strings across files.
- Store keywords and family maps in plain dicts, not class hierarchies.
