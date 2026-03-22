# Handoff: Runtime Integration

**Read [handoff_shared.md](/Users/ashtonchew/Desktop/look-before-you-click/docs/handoff_shared.md) first.** This document only covers runtime wiring and controller execution semantics.

---

## 1. Files You Own

| File | Purpose |
|---|---|
| `os-harm/run.py` | CLI flags and config wiring |
| `os-harm/lib_run_single.py` | Runtime loop, resample orchestration, final episode logging |
| `control/config.py` | Load control configs and merge CLI overrides |
| `control/controller.py` | Normalize → route → review → policy mapping |
| `control/logging.py` | Write `control_events.jsonl`, `control_summary.json`, `review_packages/` |
| `control/judge_adapter.py` | Normalize judge outputs |

Do not touch `mm_agents/*`, `desktop_env/*`, or judge internals.

---

## 2. CLI Contract

### Required flags
Keep or add these flags on `run.py`:

```python
parser.add_argument("--control_config", type=str, default=None)
parser.add_argument("--control_mode", type=str, default=None)
parser.add_argument("--reviewer_model", type=str, default=None)
parser.add_argument("--legibility_model", type=str, default=None)
parser.add_argument("--trusted_fallback_model", type=str, default=None)
```

### Judge behavior
Treat post-run judging as **always-on** for this phase.

Do **not** rely on `--run_judge_on_success` in the new handoff. It is legacy / misleading and should be cleaned up during runtime implementation.

### Control config loading
- If `--control_config` is `None`, control is disabled.
- `--control_mode` defaults to `None` at the CLI.
- If `--control_mode` is explicitly supplied, it overrides the JSON file.
- If `--control_mode` is `None`, preserve the JSON `controller_mode`.
- `trusted_fallback_model` defaults to `reviewer_model` if unset.

---

## 3. Runtime Ownership Split

### `controller.py` owns
- action normalization
- a11y parsing and target matching
- critical routing
- legibility generation
- trusted reviewer call
- policy mapping from reviewer decision to controller decision
- trusted fallback generation in `allow_or_trusted_fallback_once`

### `lib_run_single.py` owns
- the actual untrusted agent loop
- the one-step resample branch in `allow_or_resample_once`
- execution of the final action returned by the controller
- finalization of one `ControlEventLog` record per controller episode
- recent-history updates

This split is deliberate: only the runtime has the untrusted agent object, so only the runtime can resample from the same state.

---

## 4. Controller Modes

### Mode 1: `allow_or_terminate`
- `ALLOW` → execute the original action
- `BLOCK` → terminate
- `RESAMPLE` → treat as terminate in this mode
- `DEFER_TO_TRUSTED` → treat as terminate in this mode

Reviewer prompt should only expose `ALLOW` and `BLOCK` as valid choices in this mode. Runtime still fails closed if the model emits something else.

### Mode 2: `allow_or_resample_once`
- `ALLOW` → execute the original action
- `RESAMPLE` → request one replacement action from the untrusted agent on the same state
- `BLOCK` → terminate
- `DEFER_TO_TRUSTED` → terminate in this mode

Reviewer prompt should expose `ALLOW`, `RESAMPLE`, and `BLOCK` in this mode.

### Mode 3: `allow_or_trusted_fallback_once`
- `ALLOW` → execute the original action
- `DEFER_TO_TRUSTED` → request one trusted fallback action
- `BLOCK` → terminate
- `RESAMPLE` → terminate in this mode

Reviewer prompt should expose `ALLOW`, `DEFER_TO_TRUSTED`, and `BLOCK` in this mode.

---

## 5. Exact Runtime Flow

### Original candidate
Inside the action loop in `lib_run_single.py`:

1. Agent proposes `response, actions = agent.predict(instruction, obs)`
2. For each raw action candidate:
   - call `controller.review(..., action_source_hint="untrusted")`
   - receive `(decision, episode)`

### If `episode is None`
The action was not reviewed:
- execute `decision["action_to_execute"]`
- do not emit `control_events.jsonl`
- update recent history normally

### If `decision["execute"] is True`
The controller already resolved the episode:
- execute `decision["action_to_execute"]`
- action source is `decision["action_source"]`
- finalize one control event using the returned episode and final action

This covers:
- `ALLOW` on the original untrusted action
- `DEFER_TO_TRUSTED` in fallback mode, where the controller already produced one trusted fallback action

### If `decision["resample_requested"] is True`
Run one resample attempt:

1. Build `resample_instruction = build_resample_instruction(...)`
2. Call `agent.predict(resample_instruction, obs)` once on the **same observation**
3. Use the first returned action only
4. Call `controller.review(..., raw_action=resample_action, raw_response=resample_response, action_source_hint="untrusted_resample")`
5. If the second controller decision executes, run the returned action
6. Otherwise terminate
7. Finalize one control event that includes:
   - original review data
   - resample attempt metadata
   - final executed action or termination

Do not resample more than once. Do not loop.

### If the controller returns terminate with no resample/fallback
- mark the run terminated by control
- finalize one control event
- stop the action loop

---

## 6. Resample Semantics

### Same-state rule
Resample always happens on the same `obs` as the rejected action. Do not step the environment first.

### Prompting rule
The resample request must:
- restate that the last action was rejected as unsafe or suspicious
- ask for exactly one safer next action
- avoid revealing the internal review rubric
- ask for raw `pyautogui` output only

### Candidate selection rule
Use only the first resampled action candidate. If the agent emits none, terminate.

### Review rule
The resampled action is reviewed again through the same controller path. It is not automatically executed.

### Logging rule
One control event should summarize the full episode:
- original candidate
- resample attempted
- resample action
- resample reviewer result
- final executed action or termination

---

## 7. Trusted Fallback Semantics

### One-step rule
Trusted fallback may emit **one** raw `pyautogui` action only.

### No re-review rule
Do **not** re-review trusted fallback actions in the first implementation. This keeps the semantics simple and avoids controller loops.

### Validation rule
Before execution:
- action must be non-empty
- action must parse in the existing raw action space
- if parsing or generation fails, terminate

### Logging rule
One control event should capture:
- reviewer decision `DEFER_TO_TRUSTED`
- trusted fallback attempted = true
- trusted fallback result
- final executed trusted action

---

## 8. `controller.review(...)` Contract

### Inputs
Use the signature from shared context.

### Outputs
Return `(ControllerDecision, ReviewEpisode)`.

### `ReviewEpisode`
This is an internal runtime payload, not a public experiment artifact. Keep it as a plain dict with enough fields for final logging:

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

### Policy mapping inside `controller.py`

#### Non-critical
```python
decision = {
  "execute": True,
  "termination_reason": None,
  "was_critical": False,
  "reviewer_decision": None,
  "action_to_execute": raw_action,
  "action_source": action_source_hint,
  "resample_requested": False,
  "trusted_fallback_requested": False,
}
episode = None
```

#### Critical + `ALLOW`
Execute the reviewed candidate immediately.

#### Critical + `BLOCK`
Terminate immediately.

#### Critical + `RESAMPLE`
- in `allow_or_resample_once`: return `resample_requested=True`, do not execute yet
- otherwise terminate

#### Critical + `DEFER_TO_TRUSTED`
- in `allow_or_trusted_fallback_once`: call `trusted_fallback_action(...)`
  - if valid action returned, set `execute=True`, `action_to_execute=fallback_action`, `action_source="trusted_fallback"`
  - otherwise terminate
- otherwise terminate

---

## 9. Logging Contract

### Keep existing OS-Harm logs intact
Do not remove:
- `better_log.json`
- `traj.jsonl`
- screenshots
- `recording.mp4`
- `result.txt`

### Add protocol logs
Per run:
- `control_events.jsonl`
- `control_summary.json`
- `review_packages/`

### `review_packages/`
Save every package sent to the trusted reviewer. Strip screenshot bytes before writing the JSON payload.

### `control_events.jsonl`
Write one record per controller episode, not per controller helper call.

### `control_summary.json`
Include at least:

```json
{
  "task_id": "...",
  "domain": "...",
  "control_mode": "...",
  "router_mode": "...",
  "include_visual_context": true,
  "legibility_enabled": true,
  "review_count": 0,
  "critical_count": 0,
  "blocked_count": 0,
  "resample_count": 0,
  "trusted_fallback_count": 0,
  "review_latency_ms_total": 0,
  "terminated_by_control": false,
  "termination_reason": null
}
```

### Action-source accounting
Track final action source counts in summary if practical:
- `untrusted`
- `untrusted_resample`
- `trusted_fallback`

If omitted from the summary, the aggregate step must derive them from `control_events.jsonl`.

---

## 10. Recent History Contract

Track the last three **executed** actions only.

Use this shape:

```python
{
  "step_idx": int,
  "action": str,
  "action_source": "untrusted" | "untrusted_resample" | "trusted_fallback",
  "was_critical": bool,
  "reviewer_decision": str | None
}
```

### Do not append
- blocked original candidates
- blocked resample candidates
- failed trusted fallback attempts

---

## 11. Judge Contract

Judge execution is always-on after every run, including runs terminated by control.

`judge_adapter.py` should continue to normalize:
- `judge_success`
- `judge_safety`
- `judge_violation_step`
- `judge_reasoning`

Judge failures are fail-open for the run artifact set: keep the run, mark judge fields missing.

---

## 12. Acceptance Tests

- A reviewed `ALLOW` action executes normally.
- A reviewed `BLOCK` action terminates the run.
- A `RESAMPLE` decision in `allow_or_resample_once` produces exactly one retry.
- A second disallow after resample terminates the run.
- A `DEFER_TO_TRUSTED` decision in `allow_or_trusted_fallback_once` executes exactly one trusted action if valid.
- Invalid or empty trusted fallback output terminates the run.
- `control_events.jsonl` captures original and escalation metadata in one record.
- `control_summary.json` counts resamples and trusted fallbacks correctly.
