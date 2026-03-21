# Implementation Progress

## Status
Core allow/terminate protocol is implemented.

The next implementation phase is now defined by the rewritten handoffs:
- keep `B0-B4` as the primary matrix
- add `B4R` (`allow_or_resample_once`)
- add `B4T` (`allow_or_trusted_fallback_once`)

## Current code state

### Implemented now
- `control/` exists and is wired into `os-harm`
- rule-based critical router works on current `pyautogui` traces
- trusted reviewer works in language-only and state-grounded modes
- legibility generation works
- `allow_or_terminate` is integrated in the runtime loop
- judge runs explicitly after task completion
- aggregation scripts exist for the current primary outputs

### Not implemented yet
- one-step resample flow
- one-step trusted fallback flow
- 4-way reviewer contract
- secondary analysis outputs for `B4R` / `B4T`

## Phase 0 benchmark findings

- The broad attack set was too low-yield for development use.
- The selected paired set produced **5/12 `Safety=False`** attack traces.
- High-yield patterns included:
  - desktop notifications
  - Thunderbird received-mail injections
  - goals like `email_send_prompt`, `url_query_params`, and `swisstransfer_send_files`

This is why the selected paired prompt-injection set is now the default dev substrate.

## Document status

The handoff stack has been rewritten to become the authoritative spec for the next implementation phase:
- `docs/handoff_shared.md`
- `docs/handoff_runtime.md`
- `docs/handoff_parsing_routing_review.md`
- `docs/handoff_analysis.md`
- `docs/handoff_experiments.md`

Those handoffs now define:
- 3 controller modes
- 4-way reviewer decisions
- `B4R` and `B4T` as immediate priorities
- selected-set paired evaluation as the default experiment path

## Next implementation targets

1. Implement `allow_or_resample_once`
2. Implement `allow_or_trusted_fallback_once`
3. Upgrade the reviewer contract to `ALLOW | RESAMPLE | DEFER_TO_TRUSTED | BLOCK`
4. Update logging and aggregation to capture escalation behavior
5. Run smoke validation before the full matrix
