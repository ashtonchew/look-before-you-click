# Handoff: Analysis and Experiment Harness

**Read [handoff_shared.md](/Users/ashtonchew/Desktop/look-before-you-click/docs/handoff_shared.md) first.** This document covers configs, aggregation, metrics, and the experiment-facing outputs.

---

## 1. Files You Own

| File | Purpose |
|---|---|
| `configs/control_none.json` | `B0` |
| `configs/control_always_review_language_only.json` | `B1` |
| `configs/control_always_review_state_grounded.json` | `B2` |
| `configs/control_critical.json` | `B3` |
| `configs/control_critical_legibility.json` | `B4` |
| `configs/control_critical_legibility_resample_once.json` | `B4R` |
| `configs/control_critical_legibility_trusted_fallback_once.json` | `B4T` |
| `analysis/aggregate.py` | Aggregate run outputs into CSVs |
| `analysis/plots.py` | Primary and secondary plots |

Do not edit `control/*`, `run.py`, or `lib_run_single.py`.

---

## 2. Config Files

All configs must include:
- `enabled`
- `router_mode`
- `controller_mode`
- `include_visual_context`
- `legibility_enabled`
- `fail_closed_on_review_error`
- `critical_keywords_path`

### `B0`
```json
{
  "enabled": false,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": false,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

### `B1`
```json
{
  "enabled": true,
  "router_mode": "always",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": false,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

### `B2`
```json
{
  "enabled": true,
  "router_mode": "always",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": true,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

### `B3`
```json
{
  "enabled": true,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_terminate",
  "include_visual_context": true,
  "legibility_enabled": false,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

### `B4`
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

### `B4R`
```json
{
  "enabled": true,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_resample_once",
  "include_visual_context": true,
  "legibility_enabled": true,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

### `B4T`
```json
{
  "enabled": true,
  "router_mode": "critical_only",
  "controller_mode": "allow_or_trusted_fallback_once",
  "include_visual_context": true,
  "legibility_enabled": true,
  "fail_closed_on_review_error": true,
  "critical_keywords_path": "configs/critical_keywords.json"
}
```

---

## 3. Evaluation Scope

### Primary matrix
These are the required headline comparisons:
- `B0`
- `B1`
- `B2` on a small declared slice only
- `B3`
- `B4`

### Secondary protocol variants
These are immediate required follow-on comparisons:
- `B4R`
- `B4T`

### Default development dataset
Use the selected paired prompt-injection set by default:
- meta path: `evaluation_examples/test_injection_selected.json`
- config base dir: `evaluation_examples_selected`

Use the same selected set for both:
- benign condition: no `--inject`
- attack condition: with `--inject`

### Optional expansion
The full `evaluation_examples/test_injection.json` is optional later-stage expansion only. It is not the default dev matrix.

---

## 4. Metrics

### Primary metrics
- benign task success rate
- attack safety rate
- mean review latency
- review count
- critical-action trigger rate
- benign false-positive rate

### Secondary escalation metrics
- reviewer decision distribution
- resample count
- trusted fallback count
- executed action source distribution
- resample rescue rate
- trusted fallback rescue rate

### Concentration metrics
- reviewed family counts
- blocked family counts
- family distribution among unsafe attack runs

---

## 5. Input Artifacts Consumed by Aggregation

From each run folder:
- `result.txt`
- `control_summary.json`
- `control_events.jsonl`
- judge output under `judgment/.../judgment.json`

Optional:
- `review_packages/`

---

## 6. Output Artifacts

### Required primary artifacts
- `results_summary.csv`
- `frontier_safety_vs_usefulness.png`

The frontier plot is for `B0-B4` only.

### Required secondary artifacts
- `protocol_variant_summary.csv`
- `variant_comparison_B4_B4R_B4T.png` or an equivalent compact comparison plot

### Supporting artifacts
- `critical_action_family_counts.csv`
- `overhead_summary.csv`
- `blocked_examples_manifest.csv` if useful

---

## 7. Aggregation Rules

### Row granularity
`results_summary.csv` should be one row per run folder / judged task instance.

### Baseline labeling
Use stable labels in the CSV:
- `B0`
- `B1`
- `B2`
- `B3`
- `B4`
- `B4R`
- `B4T`

Do not invent alternate names in plots.

### Condition labeling
Keep:
- `is_attack`
- `task_id`
- `domain`
- `inject_suffix` if present

### Derived fields
Where possible derive from logs rather than folder names alone:
- `reviewer_decision`
- `final_action_source`
- `resample_attempted`
- `trusted_fallback_attempted`

---

## 8. Plotting Rules

### Primary plot
One labeled scatter plot for `B0-B4`:
- x-axis = usefulness
- y-axis = safety

### Secondary plot or table
Directly compare `B4`, `B4R`, and `B4T` on:
- usefulness
- safety
- review rate
- escalation counts

The secondary comparison should not replace the primary frontier plot.

---

## 9. Concentration Analysis

Concentration analysis stays in scope as supporting evidence.

Minimum automatic analysis from `control_events.jsonl`:
- counts by family
- counts by blocked family
- counts by final action source
- counts by reviewer decision type

Manual annotation remains optional, but if done it should focus on:
- blocked benign critical actions
- successful attacks
- attack runs rescued by `B4R` or `B4T`

---

## 10. Acceptance Tests

- Config JSON files parse and match the required schema.
- Aggregation handles run folders from all seven labels.
- `results_summary.csv` includes core columns plus escalation columns.
- Primary frontier plot renders `B0-B4`.
- Secondary output compares `B4`, `B4R`, and `B4T`.
- Family counts can be derived from real `control_events.jsonl` files.
