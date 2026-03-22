# Implementation Progress

## Status
Core control protocol implementation is in place.

The current phase is smoke validation and artifact verification before any further attack runs:
- verify `B4` attack artifacts
- verify `B4R` attack artifacts and at least one `RESAMPLE`
- verify `B4T` attack artifacts and at least one `DEFER_TO_TRUSTED`

## Current code state

### Implemented now
- `control/` exists and is wired into `os-harm`
- rule-based critical router works on current `pyautogui` traces
- trusted reviewer works in language-only and state-grounded modes
- legibility generation works
- all 3 controller modes are integrated in the runtime loop
- 4-way reviewer decisions are wired through controller and runtime paths
- judge runs explicitly after task completion
- aggregation scripts exist for the current primary outputs
- `B4R` and `B4T` configs, logging paths, and analysis labels are in place

### Validation still pending
- smoke validation for `B4`, `B4R`, and `B4T` attack runs
- artifact verification for `control_events.jsonl` and `review_packages/`
- confirmation that `B4R` produces `RESAMPLE` and `B4T` produces `DEFER_TO_TRUSTED`

## Phase 0 benchmark findings

- The broad attack set was too low-yield for development use.
- The selected paired set produced **5/12 `Safety=False`** attack traces.
- High-yield patterns included:
  - desktop notifications
  - Thunderbird received-mail injections
  - goals like `email_send_prompt`, `url_query_params`, and `swisstransfer_send_files`

This is why the selected paired prompt-injection set remains the default dev substrate.

## Document status

The handoff stack has been rewritten and aligned to reflect the implemented control variants:
- `docs/handoff_shared.md`
- `docs/handoff_runtime.md`
- `docs/handoff_parsing_routing_review.md`
- `docs/handoff_analysis.md`
- `docs/handoff_experiments.md`

Those handoffs now define and document:
- 3 controller modes
- 4-way reviewer decisions
- `B4R` and `B4T` as implemented protocol variants
- selected-set paired evaluation as the default experiment path

## Next validation targets

1. Verify `B4` attack smoke artifacts
2. Verify `B4R` attack smoke artifacts and `RESAMPLE` behavior
3. Verify `B4T` attack smoke artifacts and `DEFER_TO_TRUSTED` behavior
4. Resume the full matrix only after those smoke gates pass
