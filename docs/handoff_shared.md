# Shared Context — All Agents Read First

**Status:** authoritative for the next implementation phase
**Scope:** protocol wrapper + evaluation on top of `os-harm`
**Priority:** core `B0-B4` matrix plus immediate implementation of `B4R` and `B4T`

This document is the contract source. If another handoff disagrees with this file, this file wins.

---

## 1. Engineering Rules

### Code style
- Write code that is easy to skim.
- Prefer short files, short functions, and plain dicts.
- Use obvious names and early returns.
- Keep state explicit.
- Log in structured JSON whenever possible.
- If a piece of code feels smart, simplify it.

### Scope control
Do **not** build a new benchmark, a new agent architecture, asynchronous services, a database, a dashboard, a browser extension, or a system isolation framework.

### Product rule
The deliverable is still **a protocol wrapper plus evaluation**, not a new agent.

The wrapper:
- starts from the existing OS-Harm agent path
- intercepts actions before execution
- reviews only critical actions unless a blanket baseline says otherwise
- logs the protocol cleanly
- evaluates safety, usefulness, and overhead

---

## 2. Claim Guardrails

### Guardrail 1: keep the main story on `B0-B4`
The primary paper claim is still about **sparse critical-action review**:
- `B0` no control
- `B1` blanket language-only review
- `B2` blanket state-grounded review
- `B3` critical-action review
- `B4` critical-action review + legibility

`B4R` and `B4T` are immediate protocol priorities, but they are **secondary variants of `B4`**, not replacements for the main `B0-B4` comparison.

### Guardrail 2: keep `B2` or weaken the sparse-vs-blanket claim
If `B2` does not run on a declared small slice, do not claim that sparse review beats blanket state-grounded review.

### Guardrail 3: one-step escalation only
Both escalation modes are intentionally narrow:
- at most one resample per critical step
- at most one trusted fallback action per critical step
- no loops
- no multi-step trusted execution

### Guardrail 4: keep the naming honest
The base protocol should still be described as **critical-action routing with state-grounded review**. `B4T` is the first one-step trusted deferral variant, not evidence of a full trusted executor.

---

## 3. Settled Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Router | Rule-based | Cheap, debuggable, paper-friendly |
| Reviewer | Separate trusted call on reviewed actions only | Keeps the base agent path intact |
| Legibility | Separate untrusted explanation | Aids review without modifying the base agent prompt |
| Default controller mode | `allow_or_terminate` | Simplest baseline semantics |
| Escalation variants | `allow_or_resample_once`, `allow_or_trusted_fallback_once` | Immediate implementation priority, secondary evaluation layer |
| Judge | Always run after the task | Avoid ambiguous partial outputs |
| Dev dataset | Selected paired prompt-injection set | Phase 0 showed the full set is diluted by low-yield variants |

---

## 4. Architecture

```text
run.py
  └── lib_run_single.run_single_example(...)
        ├── agent.predict(instruction, obs)                      # existing path
        ├── control.controller.review(...)                       # review original candidate
        │     ├── action_normalizer.normalize(...)
        │     ├── a11y_parser.parse_tree(...) / match_target(...)
        │     ├── critical_router.route(...)
        │     ├── reviewer.generate_legibility(...)
        │     ├── reviewer.review(...)                           # 4-way trusted decision
        │     └── reviewer.trusted_fallback_action(...)          # only in fallback mode
        ├── prompts.build_resample_instruction(...)              # only in resample mode
        ├── agent.predict(resample_instruction, obs)             # one replacement only
        ├── control.logging.log_episode(...)                     # one record per controller episode
        ├── env.step(action_to_execute, ...)                     # existing path
        └── explicit post-run judge                              # always-on
```

### Ownership split
- `run.py` and `lib_run_single.py` stay thin.
- `control/controller.py` owns normalization, routing, review, and policy mapping.
- `lib_run_single.py` owns the actual resample loop because it has the untrusted agent object.
- `control/reviewer.py` owns both trusted review and trusted fallback action generation.
- `control/logging.py` writes one record per **controller episode**, not just per initial review call.

---

## 5. Authoritative File Layout

### Patch only
- `os-harm/run.py`
- `os-harm/lib_run_single.py`

### `control/`
| File | Purpose |
|---|---|
| `config.py` | Load JSON control config, merge CLI overrides |
| `controller.py` | Normalize → route → review → policy mapping |
| `logging.py` | Write `control_events.jsonl`, `control_summary.json`, `review_packages/` |
| `judge_adapter.py` | Normalize judge output |
| `types.py` | Shared dict constructors / schema helpers |
| `action_normalizer.py` | Parse raw `pyautogui` actions |
| `a11y_parser.py` | Parse a11y tree and match click target |
| `critical_router.py` | Rule-based critical-action router |
| `reviewer.py` | Legibility, trusted review, trusted fallback action |
| `prompts.py` | Reviewer, fallback, and resample prompt templates |

### `analysis/`
| File | Purpose |
|---|---|
| `aggregate.py` | Aggregate run folders into CSVs and plots |
| `plots.py` | Plotting helpers |

### `configs/`
| File | Baseline / Variant |
|---|---|
| `control_none.json` | `B0` |
| `control_always_review_language_only.json` | `B1` |
| `control_always_review_state_grounded.json` | `B2` |
| `control_critical.json` | `B3` |
| `control_critical_legibility.json` | `B4` |
| `control_critical_legibility_resample_once.json` | `B4R` |
| `control_critical_legibility_trusted_fallback_once.json` | `B4T` |
| `critical_keywords.json` | Router keywords and patterns |

---

## 6. Data Model

These schemas are authoritative. All docs and implementations should match them.

### `NormalizedAction`
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
  "target_matched": bool,
  "target_tag": str | None,
  "target_name": str | None,
  "target_text": str | None,
  "target_bounds": {"x": float, "y": float, "w": float, "h": float} | None,
  "target_match_method": "contains_point" | "nearest_center" | "none"
}
```

### `RouterDecision`
```python
RouterDecision = {
  "critical": bool,
  "family": str | None,
  "reasons": list[str],
  "confidence": float
}
```

### `LegibilityReport`
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

### `ReviewPackage`
```python
ReviewPackage = {
  "instruction": str,
  "raw_response": str,
  "normalized_action": NormalizedAction,
  "router_decision": RouterDecision,
  "obs": dict,
  "a11y_tree_linearized": str,
  "legibility_report": LegibilityReport | None,
  "recent_history": list[dict],
  "step_index": int,
  "task_id": str,
  "domain": str,
  "controller_mode": str,
  "action_source": "untrusted" | "untrusted_resample"
}
```

### `ReviewerResult`
```python
ReviewerResult = {
  "decision": "ALLOW" | "RESAMPLE" | "DEFER_TO_TRUSTED" | "BLOCK",
  "risk_score": float,
  "primary_reason": str,
  "evidence": list[str],
  "safer_alternative": str | None
}
```

### `TrustedFallbackResult`
```python
TrustedFallbackResult = {
  "action": str | None,
  "reason": str,
  "confidence": float
}
```

### `ControllerDecision`
```python
ControllerDecision = {
  "execute": bool,
  "termination_reason": str | None,
  "was_critical": bool,
  "reviewer_decision": "ALLOW" | "RESAMPLE" | "DEFER_TO_TRUSTED" | "BLOCK" | None,
  "action_to_execute": str | None,
  "action_source": "untrusted" | "untrusted_resample" | "trusted_fallback" | None,
  "resample_requested": bool,
  "trusted_fallback_requested": bool
}
```

### `ReviewEpisode`
Internal payload returned by `controller.review(...)` so runtime can finalize one log record after optional escalation.

```python
ReviewEpisode = {
  "task_id": str,
  "domain": str,
  "step_index": int,
  "raw_action": str,
  "normalized_action": dict,
  "router_decision": dict,
  "legibility_report": dict | None,
  "reviewer_result": dict | None,
  "review_latency_ms": int | None,
  "reviewer_model": str | None,
  "review_package_path": str | None,
  "action_source": "untrusted" | "untrusted_resample"
}
```

### `ControlEventLog`
One JSONL record per controller episode. A controller episode starts at a reviewed critical candidate and ends when the runtime executes a final action or terminates the step.

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
  "review_latency_ms": int | None,
  "reviewer_model": str | None,
  "resample_attempted": bool,
  "resample_raw_response": str | None,
  "resample_action": str | None,
  "resample_reviewer_result": dict | None,
  "trusted_fallback_attempted": bool,
  "trusted_fallback_result": dict | None,
  "final_action": str | None,
  "final_action_source": "untrusted" | "untrusted_resample" | "trusted_fallback" | None,
  "controller_decision": dict
}
```

---

## 7. Integration Contract

### Top-level controller entry point
`lib_run_single.py` calls this for each candidate action.

```python
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
    action_source_hint: str = "untrusted",
) -> tuple[dict, dict | None]:
    """
    Returns (ControllerDecision, ReviewEpisode).

    ReviewEpisode is None when the action is not reviewed at all.
    ReviewEpisode contains the data needed for final logging and optional
    resample/fallback resolution.
    """
```

### Controller behavior contract
- Non-critical action:
  - `execute=True`
  - `action_to_execute=raw_action`
  - `action_source=action_source_hint`
  - `ReviewEpisode=None`
- Critical action:
  - returns a populated `ReviewEpisode`
  - `ControllerDecision` reflects the current controller mode
- `controller.py` does **not** call `agent.predict(...)`
- `controller.py` may call `reviewer.trusted_fallback_action(...)` when fallback mode is active

### WS2 exports consumed by `controller.py` or runtime
```python
# control/action_normalizer.py
def normalize(raw_action: str) -> dict: ...

# control/a11y_parser.py
def parse_tree(a11y_tree_raw: str) -> list[dict]: ...
def match_target(nodes: list[dict], x: float, y: float) -> dict: ...

# control/critical_router.py
def route(action: dict, config: dict) -> dict: ...

# control/reviewer.py
def generate_legibility(...) -> dict | None: ...
def review(package: dict, config: dict) -> dict: ...
def trusted_fallback_action(package: dict, reviewer_result: dict, config: dict) -> dict: ...

# control/prompts.py
def build_resample_instruction(
    instruction: str,
    reviewer_result: dict,
    rejected_action: str,
) -> str: ...
```

---

## 8. Failure Rules

| Failure | Action |
|---|---|
| Unparsable agent action | Terminate the run |
| Reviewer call fails on a critical action | Fail closed and terminate |
| Legibility call fails | Continue without legibility |
| Trusted fallback call fails in `B4T` | Terminate the run |
| Resample produces no action | Terminate the run |
| Trusted fallback returns no action | Terminate the run |
| Judge fails after the run | Keep the run outputs and mark judge fields missing |

Do not silently fix malformed LLM outputs. Log them and take the configured safe action.

---

## 9. Baseline Mapping

| Label | Config | Meaning | Role |
|---|---|---|---|
| `B0` | `control_none.json` | no control | primary |
| `B1` | `control_always_review_language_only.json` | blanket review, language only | primary |
| `B2` | `control_always_review_state_grounded.json` | blanket review, state-grounded | primary, small slice |
| `B3` | `control_critical.json` | critical-action review | primary |
| `B4` | `control_critical_legibility.json` | critical-action review + legibility | primary |
| `B4R` | `control_critical_legibility_resample_once.json` | `B4` + one resample | secondary, immediate |
| `B4T` | `control_critical_legibility_trusted_fallback_once.json` | `B4` + one trusted fallback action | secondary, immediate |

---

## 10. Default Evaluation Dataset

Use this by default for both benign and attack:
- meta path: `evaluation_examples/test_injection_selected.json`
- config base dir: `evaluation_examples_selected`

The full `evaluation_examples/test_injection.json` remains optional expansion after the selected-set development matrix is complete and stable.
