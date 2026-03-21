# Handoff: Runtime Integration (Workstream 1)

**Read `docs/handoff_shared.md` first.** This doc covers only what WS1 owns.

---

## Files You Own

| File | What it does |
|---|---|
| `os-harm/run.py` | Patch only — add CLI flags |
| `os-harm/lib_run_single.py` | Patch only — insert controller hook |
| `control/__init__.py` | Package init (keep minimal) |
| `control/config.py` | Load JSON control config, return dict |
| `control/controller.py` | Orchestrator: normalize → route → review → policy |
| `control/logging.py` | Write `control_events.jsonl`, `control_summary.json`, save review packages |
| `control/judge_adapter.py` | Find judge output, normalize to standard fields |

## Files You Must NOT Touch

- `mm_agents/agent.py`, `desktop_env/*`, judge internals
- `control/types.py`, `control/action_normalizer.py`, `control/a11y_parser.py`, `control/critical_router.py`, `control/reviewer.py`, `control/prompts.py` — WS2 owns these
- `analysis/*`, `configs/*` — WS3 owns these

## What You Consume (from WS2)

Call these functions from `controller.py`. See exact signatures in `handoff_shared.md` §7.

- `action_normalizer.normalize(raw_action)` → NormalizedAction
- `a11y_parser.parse_tree(a11y_tree_raw)` → list of A11yNode dicts
- `a11y_parser.match_target(nodes, x, y)` → target fields to merge into NormalizedAction
- `critical_router.route(action, config)` → RouterDecision
- `reviewer.generate_legibility(instruction, obs, raw_response, action, history, config)` → LegibilityReport or None
- `reviewer.review(package, config)` → ReviewerResult

## What You Produce

- `ControllerDecision` dict (see shared context §6)
- `control_events.jsonl` — one line per reviewed action
- `control_summary.json` — per-run summary
- `review_packages/` — saved review packages on disk
- CLI flags on `run.py`
- Explicit post-run judge call

---

## 1. CLI Additions (`run.py`)

Add these flags to the `config()` function at `run.py:62–116`:

```python
# control protocol flags
parser.add_argument("--control_config", type=str, default=None,
                    help="Path to control config JSON")
parser.add_argument("--control_mode", type=str, default="allow_or_terminate",
                    help="Controller mode: allow_or_terminate, allow_or_resample_once, allow_or_trusted_fallback_once")
parser.add_argument("--reviewer_model", type=str, default=None,
                    help="Model for trusted reviewer")
parser.add_argument("--legibility_model", type=str, default=None,
                    help="Model for legibility generation")
parser.add_argument("--run_judge_on_success", action="store_true", default=True,
                    help="Run judge explicitly after task completion")
```

Stretch flags (add only when implementing those features):
- `--review_budget_target`
- `--max_resamples_per_step`

Wire the control config loading in the main `test()` function. If `--control_config` is None, control is disabled.

---

## 2. Runtime Integration Seam (`lib_run_single.py`)

The insertion point is inside the action loop at `lib_run_single.py:270–275`. Currently:

```python
for action in actions:
    logger.info(json.dumps(action, indent=2))
    action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    logger.info("Step %d: %s", step_idx + 1, action)
    obs, reward, done, info = env.step(action, args.sleep_after_execution)
```

Insert the controller call **between** the action logging and `env.step()`:

```python
for action in actions:
    logger.info(json.dumps(action, indent=2))
    action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    logger.info("Step %d: %s", step_idx + 1, action)

    # --- CONTROL PROTOCOL INSERTION ---
    if control_config and control_config.get("enabled"):
        decision = control_controller.review(
            instruction=instruction,
            obs=obs,
            raw_response=response,
            raw_action=action,
            recent_history=recent_history,
            step_idx=step_idx,
            task_id=example["id"],
            domain=example.get("domain", "unknown"),
            config=control_config
        )
        if not decision["execute"]:
            # Terminate: log reason, break out of action loop
            control_logger.log_termination(decision, step_idx, action)
            done = True
            break
    # --- END CONTROL PROTOCOL ---

    obs, reward, done, info = env.step(action, args.sleep_after_execution)
```

**Key rule (§6.2/§8.7 resolution):** When `decision["execute"]` is True, pass the original `action` (the raw string) to `env.step()`. Do NOT use `decision.action_to_execute` — that field does not exist in the MVP. Add it only when stretch modes (resample/fallback) land.

### Recent history
Track the last 3 executed actions and review outcomes in a plain list of dicts. No event bus.

```python
recent_history = []  # initialized before the while loop

# after each step, append:
recent_history.append({
    "step_idx": step_idx,
    "action": action,
    "was_critical": decision["critical"] if control_enabled else False,
    "was_allowed": decision["execute"] if control_enabled else True
})
if len(recent_history) > 3:
    recent_history.pop(0)
```

---

## 3. Controller Policy (`controller.py`)

The controller is the orchestrator. It calls WS2's modules and applies policy.

### Mode 1: `allow_or_terminate` (MVP default)
- Router says not critical → execute action
- Router says critical → run reviewer
  - Reviewer allows → execute action
  - Reviewer disallows → terminate run

### Mode 2: `allow_or_resample_once` (stretch)
- Reviewer disallows → ask agent for ONE replacement on same state
- Replacement also disallowed → terminate
- Max 1 resample per step. No loops. Do not reveal review rubric to untrusted agent.

### Mode 3: `allow_or_trusted_fallback_once` (stretch)
- Reviewer disallows → ask trusted model for ONE replacement action
- Fallback can't act confidently → terminate

### Termination semantics
When terminating on a blocked critical action:
1. End the recording
2. Write a control termination record
3. Still run the explicit post-run judge
4. Mark the run as blocked in `control_summary.json`

### Orchestration flow in `controller.review()`
```python
def review(instruction, obs, raw_response, raw_action, recent_history, step_idx, task_id, domain, config):
    # 1. Normalize action
    normalized = action_normalizer.normalize(raw_action)

    # 2. Parse a11y and match target (if click-like with coordinates)
    if obs.get("accessibility_tree") and normalized.get("x") is not None:
        nodes = a11y_parser.parse_tree(obs["accessibility_tree"])
        target_fields = a11y_parser.match_target(nodes, normalized["x"], normalized["y"])
        normalized.update(target_fields)

    # 3. Route
    router_decision = critical_router.route(normalized, config)

    if not router_decision["critical"]:
        return {"execute": True, "termination_reason": None}

    # 4. Legibility (critical only, optional)
    legibility_report = None
    if config.get("legibility_enabled"):
        legibility_report = reviewer.generate_legibility(
            instruction, obs, raw_response, normalized, recent_history, config
        )

    # 5. Build review package
    package = {
        "instruction": instruction,
        "raw_response": raw_response,
        "normalized_action": normalized,
        "router_decision": router_decision,
        "obs": obs,
        "a11y_tree_linearized": linearize_tree(obs.get("accessibility_tree", "")),
        "legibility_report": legibility_report,
        "recent_history": recent_history,
        "step_index": step_idx,
        "task_id": task_id,
        "domain": domain
    }

    # 6. Trusted review
    try:
        reviewer_result = reviewer.review(package, config)
    except Exception as e:
        if config.get("fail_closed_on_review_error", True):
            return {"execute": False, "termination_reason": "review_error_fail_closed"}
        raise

    # 7. Apply policy
    if reviewer_result["allow"]:
        return {"execute": True, "termination_reason": None}
    else:
        return {"execute": False, "termination_reason": reviewer_result["primary_reason"]}
```

---

## 4. Logging (`logging.py`)

### Keep existing logs untouched
Do not remove or replace: `better_log.json`, `traj.jsonl`, screenshots, `recording.mp4`, `result.txt`.

### Add control-specific logs
For each run, add to the result directory:
- `control_events.jsonl` — one line per reviewed action (schema: `ControlEventLog` from shared context)
- `control_summary.json` — per-run summary
- `review_packages/` — one JSON file per review package sent to the reviewer

### `control_summary.json` schema
```json
{
  "task_id": "...",
  "domain": "...",
  "control_mode": "...",
  "router_mode": "...",
  "include_visual_context": true,
  "review_count": 0,
  "critical_count": 0,
  "blocked_count": 0,
  "review_latency_ms_total": 0,
  "terminated_by_control": false,
  "termination_reason": null
}
```

### Review package storage
Save ALL review packages to disk. With 10–25 tasks and ~5–10 critical actions each, total volume is <250 packages. Don't over-engineer selective saving.

---

## 5. Judge Adapter (`judge_adapter.py`)

### Job
- Find judge output files in the run directory
- Normalize to standard fields:
  - `judge_success` — main task completion
  - `judge_safety` — attack safety evaluation
  - `judge_violation_step` — which step caused violation
  - `judge_reasoning` — judge's reasoning text

### Primary sources
- `result.txt` for main task success
- Judge safety field for attack tasks

### Failure behavior
If judge output is unavailable:
- Fall back to a clear missing-value marker
- Do not silently invent safety labels

### Explicit post-run judge call
Add a helper that always runs the judge after each task, whether the task completes normally, terminates early, or errors. Wire this into `lib_run_single.py` after the main loop exits.

---

## 6. Command Templates

### Benign paired run
```bash
python run.py \
  --path_to_vm Ubuntu/Ubuntu.vmx \
  --action_space pyautogui \
  --observation_type screenshot_a11y_tree \
  --model o4-mini \
  --judge_model gpt-4.1 \
  --result_dir ./results/paired_benign_dev \
  --test_all_meta_path evaluation_examples/test_injection.json \
  --control_config configs/control_critical_legibility.json
```

### Attack paired run
```bash
python run.py \
  --path_to_vm Ubuntu/Ubuntu.vmx \
  --action_space pyautogui \
  --observation_type screenshot_a11y_tree \
  --model o4-mini \
  --judge_model gpt-4.1 \
  --result_dir ./results/paired_attack_dev \
  --test_all_meta_path evaluation_examples/test_injection.json \
  --inject \
  --control_config configs/control_critical_legibility.json
```

### No-control baseline
```bash
python run.py \
  --path_to_vm Ubuntu/Ubuntu.vmx \
  --action_space pyautogui \
  --observation_type screenshot_a11y_tree \
  --model o4-mini \
  --judge_model gpt-4.1 \
  --result_dir ./results/baseline_none \
  --test_all_meta_path evaluation_examples/test_injection.json \
  --inject \
  --control_config configs/control_none.json
```

---

## 7. Definition of Done

### Phase 0 — Repo sanity
- One OS-Harm task runs locally
- One prompt-injection task runs with `--inject`
- Same task runs without `--inject`
- Output folder structure is understood

### Phase 1 — Review seam
- Controller hook exists between `agent.predict` and `env.step`
- Raw action and observation pass into `control.controller.review(...)`
- Control logs are written
- End-to-end run works with a dummy reviewer that always allows

### Acceptance tests
- Critical step generates a `control_events.jsonl` entry
- Disallowed action terminates run cleanly and still runs judge
- Judge runs after normal completion
- End-to-end run works with a dummy reviewer that always allows
