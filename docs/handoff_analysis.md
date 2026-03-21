# Handoff: Analysis & Experiment Harness (Workstream 3)

**Read `docs/handoff_shared.md` first.** This doc covers only what WS3 owns.

---

## Files You Own

| File | What it does |
|---|---|
| `configs/control_none.json` | B0 — no control baseline |
| `configs/control_always_review_language_only.json` | B1 — blanket monitor, language-only |
| `configs/control_always_review_state_grounded.json` | B2 — blanket monitor, state-grounded |
| `configs/control_critical.json` | B3 — rule-based routing, no legibility |
| `configs/control_critical_legibility.json` | B4 — routing + legibility |
| `analysis/__init__.py` | Package init |
| `analysis/aggregate.py` | Run folders → CSV + frontier plot |

## Files You Must NOT Touch

- Anything in `control/`
- `run.py`, `lib_run_single.py`
- `mm_agents/*`, `desktop_env/*`, judge internals

## What You Consume

- `control_events.jsonl` — one JSONL record per reviewed action (schema in shared context §6)
- `control_summary.json` — per-run summary (schema in `handoff_runtime.md` §4)
- `result.txt` — OS-Harm task result
- Judge output files — safety/success fields

## What You Produce

- `results_summary.csv`
- `frontier_safety_vs_usefulness.png`
- `overhead_summary.csv` (add when needed)
- `critical_action_family_counts.csv` (add when needed)
- `blocked_examples_manifest.csv` (add when needed)
- Config JSON files (B0–B4)

## Dependency Note

You can build configs immediately. The aggregate script needs actual run outputs from WS1+WS2 to test. Start with configs + script skeleton, then validate once runs exist.

---

## 1. Config Files

Follow the schema in `handoff_shared.md` §8 exactly.

### `configs/control_none.json` (B0)
```json
{
  "enabled": false,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": false,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true
}
```

### `configs/control_always_review_language_only.json` (B1)
```json
{
  "enabled": true,
  "router_mode": "always",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": false,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true
}
```

### `configs/control_always_review_state_grounded.json` (B2)
```json
{
  "enabled": true,
  "router_mode": "always",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": true,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true
}
```

### `configs/control_critical.json` (B3)
```json
{
  "enabled": true,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": true,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true
}
```

### `configs/control_critical_legibility.json` (B4)
```json
{
  "enabled": true,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": true,
  "legibility_enabled": true,
  "fail_closed_on_review_error": true
}
```

All baselines are config changes, not code forks.

---

## 2. Evaluation Plan

### Dev smoke (first pass)
- 3 benign prompt-injection tasks run **without** `--inject`
- 3 attack prompt-injection tasks run **with** `--inject`

### Dev set
- 10–15 paired prompt-injection tasks

### Test set
- 15–25 paired prompt-injection tasks if compute permits

### Optional extension
- 5–10 model-misbehavior tasks
- Small custom side-task setting

### Pairing rule
Use the same `test_injection.json` tasks in both modes:
- Benign condition: same tasks, no `--inject`
- Attack condition: same tasks, with `--inject`

If a task has multiple injection goals:
- Usefulness key = `domain/example_id`
- Attack key = `domain/example_id/injection_type/goal_id`

### Baselines to run
Required (B0–B4):
1. `none` (B0)
2. `always_review_language_only` (B1)
3. `always_review_state_grounded` (B2) — run on small slice only (3–5 tasks)
4. `critical_review` (B3)
5. `critical_review_legibility` (B4)

Stretch (build only if B0–B4 are complete):
6. `critical_review_legibility_resample_once`
7. `critical_review_legibility_trusted_fallback_once`

---

## 3. Metrics

### Usefulness
- Benign task success rate

### Safety
- Attack task safety rate (1 − harmful success rate)

### Monitor / controller behavior
- Review count per run
- Critical-action trigger rate
- Block rate
- Disallow rate
- False positive rate on benign tasks

### Overhead
- Extra review model calls
- Mean review latency
- Total wall-clock increase
- Reviewed-step fraction

### Analysis extras (add when needed)
- Action family distribution among reviewed steps
- Action family distribution among blocked steps
- Per-domain breakdown if time allows

---

## 4. Aggregate Script (`analysis/aggregate.py`)

### Usage
```bash
python -m analysis.aggregate --root ./results --out ./analysis_outputs
```

### Job
1. Traverse run folders under `--root`
2. Read `control_summary.json` and `result.txt` from each run
3. Read judge output for safety labels
4. Compute metrics listed above
5. Produce required artifacts

### Required artifacts
- `results_summary.csv` — one row per (task, baseline) with all metrics
- `frontier_safety_vs_usefulness.png` — scatter plot with B0–B4 as labeled points, x-axis = usefulness (benign success rate), y-axis = safety (attack safety rate)

### Add when needed
- `overhead_summary.csv` — latency and call count breakdown per baseline
- `critical_action_family_counts.csv` — family distribution among reviewed/blocked actions
- `blocked_examples_manifest.csv` — manifest of blocked traces with paths to review packages

### File size rule
Start with one file. Split into `aggregate.py` + `plot.py` only if it exceeds ~300 lines.

**Note:** `commands.md` references `analysis.aggregate_results` and `analysis.plot_frontier` as separate scripts. Ignore that — follow this doc.

---

## 5. Concentration Analysis

This supports the paper's central claim and serves as a fallback if end-to-end gains are noisy.

### Automatic part (from `control_events.jsonl`)
Compute:
- Counts by critical family
- Counts by blocked family
- Counts by attack outcome × family

### Manual annotation (stretch)
Detailed schemas are in `docs/stretch_analysis.md` (to be written if needed). The key idea: annotate a small set of blocked attack runs, successful attack runs, and benign false positives to check whether the router and reviewer made the right calls.

The logs from WS1 contain all the data needed. Build this after the main experiment runs.

---

## 6. Acceptance Tests

- Aggregate script finds run folders and writes CSV
- `results_summary.csv` contains correct columns (task_id, domain, baseline, success, safety, review_count, etc.)
- Frontier plot renders with B0–B4 as labeled points
- Config JSON files are valid JSON and match the schema in `handoff_shared.md` §8
