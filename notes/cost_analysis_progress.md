# Cost Analysis Progress

**Date**: 2026-03-22
**Status**: Complete

## What was built

Added retrospective cost estimation as a third metric dimension alongside safety and usefulness. The implementation estimates USD cost per control event from existing experiment logs using known prompt sizes and model pricing, without requiring re-runs.

### New files
- `analysis/cost_estimator.py` -- Core estimation: `MODEL_PRICING`, `screenshot_tokens()` (model-dependent), `estimate_event_cost()`, `estimate_run_cost()`, CLI with `main()`
- `tests/test_cost_estimator.py` -- 24 unit tests covering screenshot token formulas, per-call cost computation, edge cases

### Modified files
- `analysis/aggregate.py` -- Cost accumulation in `parse_run_folder()`, cost metrics in `compute_baseline_metrics()`, `estimated_cost_usd` in `CSV_COLUMNS`, cost columns in `_OVERHEAD_CSV_COLUMNS`, `$/Task` column in printed metrics table, cost bar chart call in `main()`
- `analysis/plots.py` -- Added `write_cost_bar_chart()` using `BASELINE_COLORS`, matching existing plot conventions
- `analysis/ablation_ladder.py` -- Added `mean_cost_per_task_usd` to `_compute_metrics()` and `write_metrics_csv()`, `cost/task` in printed output
- `tests/test_aggregate_smoke.py` -- Added `test_cost_column_present` assertion
- `tests/test_ablation_ladder.py` -- Added `test_csv_has_cost_column` assertion

## Actual numbers (from experiment logs)

### Per-call costs

| Call | Model | Visual cost | Text-only cost |
|------|-------|-------------|----------------|
| Legibility | gpt-4o-mini | $0.000572 | N/A (always visual) |
| Review | gpt-5.4-mini | $0.003627 | $0.001575 |
| Trusted fallback | gpt-5.4-mini | ~$0.003550 | ~$0.001350 |

### Per-baseline cost (environmental ablation ladder)

| Baseline | Runs | Reviews | Rev/Run | $/Task | $/Review | Safety | Useful |
|----------|------|---------|---------|--------|----------|--------|--------|
| B0 | 17 | 0 | 0 | $0.0000 | -- | 58.3% | 60.0% |
| B1 | 17 | 39 | 2.29 | $0.0036 | $0.0016 | 83.3% | 0.0% |
| B2 | 17 | 45 | 2.65 | $0.0096 | $0.0036 | 100% | 40.0% |
| B3 | 17 | 8 | 0.47 | $0.0017 | $0.0036 | 91.7% | 60.0% |
| B4 | 17 | ~9 | ~0.53 | $0.0023 | $0.0043 | 66.7% | 40.0% |

(B4 environmental has 17 env runs out of 41 total; 9 of 24 reviews are from env runs)

### Cost ordering

B0 ($0) < B3 ($0.0017) < B4 ($0.0023) < B1 ($0.0036) < B2 ($0.0096)

## Key findings

1. **B3 is 17.8% of B2 cost per task** -- selective routing cuts cost 5.6x while achieving 91.7% vs 100% safety
2. **B3 and B2 have identical per-review cost ($0.0036)** -- the cost difference is entirely driven by review count (0.47 vs 2.65 reviews/run)
3. **Legibility overhead is $0.000572/call** (13.2% of B4 per-action cost) -- cheap relative to the gpt-5.4-mini reviewer call, but the associated safety drop (91.7% to 66.7%) makes it counterproductive
4. **gpt-5.4-mini reviewer call is the dominant cost driver** at $0.003627 per visual review (5x more expensive than gpt-4o-mini on input, 7.5x on output)
5. **Total control overhead is negligible in absolute terms** ($0.002-$0.010/task) but the 5.6x ratio between B3 and B2 quantifies selective routing's value

## Token estimation methodology

### Model pricing (March 2026)
- gpt-4o-mini: $0.15/1M input, $0.60/1M output
- gpt-5.4-mini: $0.75/1M input, $4.50/1M output

### Screenshot tokens (model-dependent)
- gpt-4o-mini (old tile formula): 1920x985 -> 6 tiles -> 85 + 170*6 = 1105 tokens
- gpt-5.4-mini (new patch formula): 1920x985 -> 60*31=1860 patches -> capped at 1536 tokens

### Text token estimates (from prompt template analysis)
- Review input (text-only): ~1200 tokens
- Review input (visual, no legibility): ~2400 text + screenshot
- Review input (visual + legibility): ~2590 text + screenshot
- Review output: ~150 tokens
- Legibility input: ~1950 text + screenshot
- Legibility output: ~190 tokens

## Caveats

- Token counts are estimated from prompt structure, not measured from API `response.usage`
- Prompt caching (90% input discount) and batch API (50% off) were not used in experiments
- The gpt-5.4-mini screenshot formula may include an unconfirmed mini multiplier (1.62x)
- Pricing as of March 2026; costs trend downward
- Small N (5-12 tasks per condition); cost differences are deterministic given review counts

## Artifacts generated

- `overhead_summary.csv` -- now includes `total_cost_usd`, `mean_cost_per_task_usd`, `mean_cost_per_review_usd`
- `results_summary.csv` -- now includes `estimated_cost_usd` per run
- `cost_per_task_by_baseline.png` -- bar chart of $/task by baseline
- `cost_by_baseline.csv` -- standalone cost-only summary (from CLI)
- `ablation_ladder_metrics.csv` -- now includes `mean_cost_per_task_usd`

## Paper integration

### Overhead table
Add `Control cost/task` column to the existing overhead or ablation ladder table. The numbers are small enough to report in the table without a separate figure, though the bar chart provides visual impact.

### Claims supported
1. "Selective visual review (B3) achieves the best safety/usefulness tradeoff at 17.8% of blanket visual review (B2) cost"
2. "The cost difference is driven entirely by review count -- selective routing reduces reviews from 2.65/task to 0.47/task"
3. "Legibility adds $0.0006/call but is associated with a 25pp safety drop (91.7% to 66.7%)"

### Suggested wording
In the overhead discussion: "Table N reports estimated control overhead cost per task. B3 (selective, visual) costs $0.0017/task compared to B2 (blanket, visual) at $0.0096/task -- a 5.6x reduction driven entirely by review count, since per-review costs are identical at $0.0036. The dominant cost component is the gpt-5.4-mini reviewer call with screenshot tokens."

## What's left (post-hackathon)

- Forward instrumentation: capture `response.usage` from `_call_openai()` / `_call_anthropic()` in `control/reviewer.py`
- Store actual token counts in `control_events.jsonl`
- Verify gpt-5.4-mini screenshot multiplier empirically
- Replace estimation with precise measurement in aggregate pipeline
