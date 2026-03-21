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
11. [ ] Implement `allow_or_resample_once` (`B4R`) as immediate priority.
12. [ ] Implement `allow_or_trusted_fallback_once` (`B4T`) as immediate priority.
13. [ ] Validate all three controller modes on smoke runs.
14. [ ] Run the core `B0-B4` matrix on the selected paired set.
15. [ ] Run `B4R` and `B4T` as secondary protocol variants.
16. [ ] Finish concentration analysis from control logs.

**Current state:** allow/terminate is implemented; resample and trusted fallback are the next implementation targets, not deferred stretch work.

## What's next

Implement the rewritten handoffs, then run the updated experiment order from `docs/handoff_experiments.md`.
