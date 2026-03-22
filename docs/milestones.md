# Milestones

If time is collapsing, do these in order and stop when needed.

1. [x] One paired benign vs attack run works (same task, +/- `--inject`) -- Phase 0 complete. Broad attack set was low-yield, but the selected paired set produced 5/12 `Safety=False` attack traces. See `notes/phase0_progress.md`.
2. [x] Controller seam exists between `agent.predict` and `env.step`.
3. [x] Rule-based critical router works on common `pyautogui` actions.
4. [x] Trusted reviewer works in state-grounded mode.
5. [x] `allow_or_terminate` works end-to-end.
6. [x] Explicit post-run judge path works.
7. [x] Aggregate CSV + primary frontier plot exist, pending validation on real multi-baseline data.
8. [x] Legibility path works.
9. [x] Always-review baselines exist.
10. [x] Handoff rewrite for the next implementation phase exists.
11. [x] Implement `allow_or_resample_once` (`B4R`).
12. [x] Implement `allow_or_trusted_fallback_once` (`B4T`).
13. [x] Wire all three controller modes and the 4-way reviewer/runtime contract end-to-end.
14. [ ] Validate all three controller modes on smoke runs.
15. [ ] Verify smoke artifacts for `B4`, `B4R`, and `B4T`.
16. [ ] Run the core `B0-B4` matrix on the selected paired set.
17. [ ] Run `B4R` and `B4T` as secondary protocol variants.
18. [ ] Finish concentration analysis from control logs.

**Current state:** all three controller modes and the 4-way reviewer/runtime wiring are implemented. The current phase is smoke validation and artifact verification before resuming attack runs.

## What's next

Finish manual smoke validation in this order: `B4` attack, `B4R` attack, `B4T` attack. Once those artifact gates pass, continue the experiment order from `docs/handoff_experiments.md`.
