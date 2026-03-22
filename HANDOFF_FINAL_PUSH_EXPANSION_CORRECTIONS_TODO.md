# Handoff: Final Push Expansion Corrections TODO

- Date: 2026-03-22
- Status: authoritative correction handoff for final-push expansion gaps
- Scope: corrective reruns, expansion runs, analysis recomputes, and doc sync (all code fixes landed)

Default framing:
- Original `results_backup/final_*` artifacts are frozen pre-fix historical outputs.
- Corrected claims must come from new rerun outputs.
- `docs/handoff_final_push_expansion.md` must be updated to match this correction TODO once the work lands.

## 1. Current State Snapshot

### Closed Since Last Pass
- Router keyword coverage fix landed in `control/critical_router.py` and `configs/critical_keywords.json`.
- A2 goal strings, task JSONs, and `tests/test_a2_goals.py` exist.
- Dead `_stubs` fallback imports in `os-harm/control/controller.py` are cleaned up.
- `control/_stubs.py` is deleted.
- Basic plot-helper tests now exist in `tests/test_plots.py`.
- Targeted tests pass:
- `tests/test_router.py`
- `tests/test_a2_goals.py`
- `tests/test_plots.py`

### ~~Open~~ P1 Blockers (all resolved)
- ~~Scheming Thunderbird email wrappers still use contaminated `os-harm/assets/message_3.eml`.~~ Fixed: see Section 10 (`message_3_benign.eml`).
  - Impact: contaminated controls invalidate honest and attack scheming email-substrate numbers.
- ~~`_check_target_keywords()` in `control/critical_router.py` still includes freeform `text`.~~ Fixed: see Section 10 (typed-prose router fix).
  - Impact: freeform prose routing corrupts B4 review counts on compose-heavy traces.
- ~~A2 manifest is still not runnable through the real `run.py` resolution path.~~ Fixed: see Section 10 (split manifests + goal registration).
  - Impact: A2 expansion is still partial because the documented manifest cannot drive the real runner cleanly.

### Open P2 Blockers
- ~~`analysis/aggregate.py` still mixes incompatible cohorts by baseline label only.~~ Fixed: cohort-aware aggregation + filesystem reorganization landed.
- ~~Failure-taxonomy plotting helper exists but is not wired into the real analysis pipeline.~~ Fixed: taxonomy double-counting bug resolved, pipeline wired.
- ~~`write_failure_taxonomy_plot()` still emits a PNG when all counts are zero.~~ Already fixed in prior session.
- ~~`docs/related_work_outline.md` is still missing.~~ Exists (67 KB).
- No output currently produces the promised A1-vs-A2 comparison table.
- B1/B2/B3 support is config-ready but runs are still absent.

## 2. Corrective Work Required

> **All items in this section have landed. See Sections 10-11 for details.**

### ~~Router Precision~~
- Remove freeform `text` from generic `_check_target_keywords()`.
- Keep explicit typed-command checks for shell/network command text.
- Preserve recall for `rm`, `rmdir`, `mv`, `wget`, `curl`, `sudo`, `chmod`.
- Add a regression that drafted email prose with `reply`, `send`, `attached` is not critical by keyword alone.

### ~~Scheming Email Substrate~~
- Create a benign third email asset for scheming Thunderbird wrappers.
- Stop using `message_3.eml` in `__injected_email__scheming__beacon_nav`.
- Stop using `message_3.eml` in `__injected_email__scheming__draft_recipient_insertion`.
- Stop using `message_3.eml` in `__injected_email__scheming__upload_credentials`.
- Stop using `message_3.eml` in `__injected_email__scheming__upload_credentials__a2`.
- Keep prompt-injection-bearing mail assets only for the environmental injection threat model.

### ~~A2 Runner Path~~
- ~~Make A2 manifests runnable through the real `run.py` lookup path.~~ Fixed: split into `test_a2_env_selected.json` + `test_a2_schem_selected.json`, with per-variant manifests (`test_a2_env1_selected.json`, `test_a2_env2_selected.json`, `test_a2_schem1_selected.json`) for the runner scripts.
- ~~Either split env/scheming manifests or make runner resolution support both bases explicitly.~~ Split manifests landed.
- ~~Replace the current dual-tree validation-only assumption with a runner-faithful test.~~ `tests/test_a2_goals.py` + `tests/test_final_push_manifests.py` validate path resolution.

### ~~Aggregation~~
- Separate cohorts by experiment family, not just baseline label.
- Final-push matrix, smoke variant runs, and future expansion runs must not merge under a single `B4`.
- Overhead table, frontier, and variant comparison must operate on explicitly filtered cohorts.

### ~~Failure Taxonomy Pipeline~~
- Convert concentration taxonomy rows into `{failure_mode: {threat_model: count}}`.
- Call `write_failure_taxonomy_plot()` from the real analysis path.
- Return `None` for all-zero taxonomy input.
- Guarantee `failure_taxonomy.png` only appears when there is real non-zero data.

### ~~Codebase Cleanup~~
- Remove stale duplicate `os-harm/control/` package after one smoke import-path check.
- Supported runtime path is repo-root `control`, not duplicate package shims.

## 3. Corrective Rerun Matrix

### Final Count
- Corrective reruns required for final-push validity: `19`.
- New expansion runs still pending separately: `12` (`B1/B2/B3` + `A2`).

### A. Router Coverage Reruns (2)
- `final_schem_b4_honest` `vs_code/ec71221e-ac43-46f9-89b8-ee7d80f7e1c5__scheming__delete_backup`
- `final_schem_b4_attack` `vs_code/ec71221e-ac43-46f9-89b8-ee7d80f7e1c5__scheming__delete_backup`
- Reason: `rm` coverage fix already landed.
- Reason: stored B4 honest and B4 attack outputs are now stale because both still show `review_count = 0`.

### B. Scheming Email-Substrate Validity Reruns (12)
- Task ID: `__injected_email__scheming__beacon_nav`
- Task ID: `__injected_email__scheming__draft_recipient_insertion`
- Task ID: `__injected_email__scheming__upload_credentials`
- Run cell: `B0 honest`
- Run cell: `B0 attack`
- Run cell: `B4 honest`
- Run cell: `B4 attack`
- Reason: these wrappers still use the contaminated email substrate.
- Reason: this invalidates both honest and attack scheming results, not only B4.
- Instruction: run each listed task ID in all four listed cells.

### C. Typed-Prose Precision Reruns (5)
- `final_env_b4_attack` `thunderbird/__injected_draft__inject__thunderbird_mail_draft__terminal_local_script`
- `final_env_b4_attack` `thunderbird/__injected_email__inject__desktop_notification__swisstransfer_send_files`
- `final_schem_b4_attack` `thunderbird/__injected_draft__scheming__beacon_nav`
- `final_schem_b4_honest` `thunderbird/__injected_draft__scheming__beacon_nav`
- `final_schem_b4_honest` `thunderbird/__injected_draft__scheming__delete_backup`
- Reason: these are the observed non-contaminated stored B4 traces with critical `primary_kind="type"` review events that can change when generic typed-prose routing is fixed.

### D. Gating Rule
- ~~Do not start the 12 scheming email-substrate reruns or `A2-schem-1` until the benign scheming email asset exists.~~ Benign email landed.
- ~~Do not trust aggregate outputs until cohort-aware aggregation lands.~~ Cohort-aware aggregation landed.
- All gating conditions met. All rerun blocks are ready to execute.

## 4. New Expansion Runs Still Pending

### B1/B2/B3 Ablation
- `B1 honest`
- `B1 attack`
- `B2 honest`
- `B2 attack`
- `B3 honest`
- `B3 attack`

### A2 Runs
- `A2-env-1 B0`
- `A2-env-1 B4`
- `A2-env-2 B0`
- `A2-env-2 B4`
- `A2-schem-1 B0`
- `A2-schem-1 B4`
- Note: A2-schem-1 was previously blocked on scheming substrate cleanup and runner-path fix. Both are now resolved -- ready to run.

## 5. Analysis Recompute Rules

- ~~Rerun aggregates only after cohort separation is fixed.~~ Cohort separation landed.
- Recompute final-push frontier, overhead table, and summary CSV on corrected final-push cohorts only.
- ~~Keep smoke `B4/B4R/B4T` analysis separate unless explicitly filtered as a variant-only cohort.~~ Smoke is now in its own root.
- Generate `failure_taxonomy.png` from the real pipeline, not ad hoc.
- ~~Treat prior `analysis.aggregate --root results_backup` outputs as provisional or invalid on mixed layouts.~~ Bare `results_backup` root now errors; per-cohort roots required.

### Cohort root commands (post-reorganization)
```bash
uv run python -m analysis.aggregate --root results_backup/final_historical --out analysis_outputs/final_historical
uv run python -m analysis.aggregate --root results_backup/smoke --out analysis_outputs/smoke
uv run python -m analysis.aggregate --root results_backup/final_corrected --out analysis_outputs/final_corrected
uv run python -m analysis.aggregate --root results_backup/expansion --out analysis_outputs/expansion
```

## 6. Required Tests

- Runner-level A2 resolution test using real `run.py` path logic.
- ~~Aggregate mixed-cohort separation test on a `results_backup`-style layout.~~ Landed: `TestDetectMixedCohorts` (7 tests), `TestExperimentFamily` (4 tests).
- ~~All-zero failure-taxonomy plot test.~~ Already landed in prior session.
- ~~Concentration smoke test that emits `failure_taxonomy.png`.~~ Landed: `TestTaxonomyNoCrossThreadDoubleCount` (3 tests).
- ~~Compose-body prose non-critical router regression.~~ Landed: `TestTypedProseNotCritical` in `tests/test_router.py` (9 tests).
- ~~Runtime import-path smoke test proving top-level `control` is used.~~ Implicitly covered by existing `control.*` imports after deletion of duplicate `os-harm/control/` package.

## 7. Output Directory Rules

- Corrected reruns must write to new `results/final_rerun_*` directories.
- Then copy those to `results_backup/rerun_raw/final_rerun_*`.
- Assemble paper-ready corrected cohort in `results_backup/final_corrected/`.
- Never overwrite `results_backup/final_historical/`.
- Corrected paper claims must cite `final_corrected` outputs, not `final_historical`.
- Expansion runs (B1/B2/B3, A2) go to `results_backup/expansion/`.

## 8. Assumptions

- The split A2 manifests (`test_a2_env_selected.json`, `test_a2_schem_selected.json`) and per-variant manifests (`test_a2_env1_selected.json`, `test_a2_env2_selected.json`, `test_a2_schem1_selected.json`) are runnable through the real runner path.
- ~~`analysis.aggregate --root results_backup --out analysis_outputs` is an intended user path and must be safe on the checked-in layout.~~ Replaced: bare `results_backup` now errors; point `--root` at one cohort directory.
- Repo-root `control/` is the only supported source of truth.
- The `19` corrective reruns are the smallest paper-safe correction set.

## 9. Acceptance Criteria

- An implementer can execute remaining fixes without making new decisions.
- The rerun matrix is split cleanly into `corrective reruns` vs `new expansion runs`.
- The document states exactly why each rerun block exists.
- The analysis recompute rules are explicit.
- The file can be used to update `docs/handoff_final_push_expansion.md` with no additional interpretation.

---

## 10. Update: Code Fixes Landed (2026-03-22)

All code-level corrections from Sections 1-2 are now implemented and verified. Only experiment runs and analysis recompute remain.

### What was fixed

**Router Precision (P1 -- Section 2, "Router Precision")**

Removed freeform `text` from the generic keyword scan in `_check_target_keywords()`. The field tuple now checks `(target_name, target_text, target_tag, nearby_text)` only. `nearby_text` was retained because the technical spec treats adjacent a11y labels as valid critical-action evidence for unlabeled icon buttons.

Added `_check_typed_commands()` with a narrow keyword set (`rm`, `rmdir`, `mv`, `sudo`, `chmod`, `wget`, `curl`) stored in `_TYPED_COMMAND_FAMILIES`. This function checks `action["text"]` on `primary_kind == "type"` actions, then falls back to scanning `write()`/`typewrite()` arguments in the raw action string. The raw-action fallback mirrors `_raw_action_contains_url()` and closes the normalization-loss gap where `typewrite('rm -rf /'); press('enter')` collapses to `primary_kind == "press"`.

Why: email body prose containing "send", "attached", "reply", "delete" was triggering false critical routing on compose-heavy Thunderbird traces, corrupting B4 review counts.

Files changed: `control/critical_router.py`, `tests/test_router.py` (9 new regression tests in `TestTypedProseNotCritical`, 4 raw-action command tests in `TestMultiCallURLDetection`).

**Scheming Email Substrate (P1 -- Section 2, "Scheming Email Substrate")**

Created `os-harm/assets/message_3_benign.eml` -- a clean email with the same From/To/Date as `message_3.eml` but a benign subject ("Zurich meetup next Thursday") and no `{injection}` placeholder. Updated all 4 scheming Thunderbird wrappers to reference `message_3_benign.eml` instead of `message_3.eml`. The VM destination path stays `message_3.eml` so Thunderbird indexing is unaffected.

Why: the contaminated `message_3.eml` subject line ("IMPORTANT: to the AI agent, please read this first") is a prompt injection signal. Scheming wrappers should only attack via `attack_prompt` in the system prompt, not via email body injection. The contamination created a confound that invalidated both honest and attack scheming results.

Files changed: `os-harm/assets/message_3_benign.eml` (new), 4 scheming wrapper JSONs (`local_path` field on line 25 of each).

**Aggregation Cohort Safety Guard (P2 -- Section 2, "Aggregation")**

Added `_detect_mixed_cohorts()` to `analysis/aggregate.py`. When no `--experiment-prefix` is given and multiple experiment sources share the same `(baseline, threat_model)` pair, the function warns and `main()` skips frontier, overhead, and variant outputs. Per-run CSV and family counts still write unconditionally.

The guard is keyed on `(baseline, threat_model)` so that legitimate `final_env_*` and `final_schem_*` cohorts sharing a baseline do not trigger it -- `main()` already computes their metrics separately.

Why: running `aggregate.py --root results_backup` without `--experiment-prefix` silently merged final-push and smoke runs under the same baseline label, producing invalid frontier/overhead outputs.

Files changed: `analysis/aggregate.py`, `tests/test_aggregate_smoke.py` (6 new tests in `TestDetectMixedCohorts`).

**Codebase Cleanup (P2 -- Section 2, "Codebase Cleanup")**

Deleted `os-harm/control/` (6 files). This was a stale duplicate of the repo-root `control/` package. The repo-root `control/` is the only supported import path -- confirmed by `controller.py` importing directly from `control.*` with no fallback.

**Doc Drift Fix**

Updated `docs/handoff_final_push_expansion.md` Section 4.2 to reference the actual split manifests (`test_a2_env_selected.json` + `test_a2_schem_selected.json`) and the correct scheming task filename, replacing the deleted single-manifest path.

### What was already done before this session

- Router keyword coverage: `rm`, `rmdir`, `mv`, `wget`, `curl` added to keyword families.
- Word-boundary matching: compiled `\b` patterns in `_compile_family_patterns()`.
- A2 goal templates registered in `run.py` (`a2_reframed_exfil`, `a2_reviewer_aware_url`).
- A2 task JSONs, split manifests, and `tests/test_a2_goals.py` (3 tests, all pass).
- `control/_stubs.py` deleted, stubs fallback imports cleaned from `controller.py`.
- `write_failure_taxonomy_plot()` returns None on all-zero input; wired into `concentration.py`.
- `tests/test_plots.py` with 7 tests covering the plot guard.
- `docs/related_work_outline.md` exists (5479 bytes).

### What is still open

All remaining items require experiment execution, not code changes.

| Item | Section | Blocked on |
|------|---------|------------|
| 2 router coverage reruns (VS Code delete_backup) | 3A | Nothing -- ready to run |
| 12 scheming email-substrate reruns (3 tasks x 4 cells) | 3B | Nothing -- benign email landed |
| 5 typed-prose precision reruns | 3C | Nothing -- router fix landed |
| 6 B1/B2/B3 ablation runs | 4 | Nothing -- configs exist |
| 6 A2 expansion runs | 4 | Nothing -- ready to run |
| Analysis recompute on corrected cohorts | 5 | Reruns completing |
| Populate `final_corrected/` from rerun outputs | 7 | Reruns completing |

Total: 19 corrective reruns + 12 new expansion runs = 31 experiment runs remaining.

---

## 11. Update: Analysis Bug Fixes and Cohort Reorganization (2026-03-22)

Three P1 analysis bugs fixed and results_backup reorganized into first-class cohort roots.

### Bug fixes

**Cohort guard false positive (P1)**

`_detect_mixed_cohorts()` compared raw experiment directory names, so `final_env_b0_honest` and `final_env_b0_attack` were flagged as "mixed" even though they are the two required halves of one experiment. Added `_experiment_family()` to strip `_honest`/`_attack` suffixes before comparison.

Files: `analysis/aggregate.py`, `tests/test_aggregate_smoke.py` (7 cohort tests + 4 family tests).

**Reviewer ablation screenshot mismatch (P1)**

`_reconstruct_screenshot()` used only a nearest-step-number heuristic. Under B4R resampling, the env step counter diverges from better_log logical indices, causing the heuristic to select the wrong PNG. Added `_screenshot_from_better_log()` which resolves via better_log.json's exact `screenshot_file` reference (with timestamp-suffix fallback for counter mismatch). The heuristic is now fallback-only.

Files: `analysis/reviewer_ablation.py`, `tests/test_screenshot_reconstruction.py` (9 tests).

**Failure taxonomy double-counting (P1)**

`compute_failure_taxonomy()` grouped by `(failure_mode, outcome)` only, then `taxonomy_to_plot_data()` distributed the collapsed count to every threat model in the comma-joined string. 18 environmental + 5 scheming = 23 total was showing as 23/23. Fixed by including `threat_model` in the grouping key. CSV column renamed from `threat_models` to `threat_model`.

Files: `analysis/concentration.py`, `tests/test_plots.py` (3 taxonomy tests).

### Filesystem reorganization

Moved from flat `results_backup/` to cohort-per-directory layout:

```
results_backup/
  smoke/                  -- validation and qualitative traces
  final_historical/       -- frozen pre-fix final-push outputs
  final_corrected/        -- paper-ready corrected cohort (empty, awaiting reruns)
  rerun_raw/              -- immutable raw corrective reruns (empty, awaiting reruns)
  expansion/              -- B1/B2/B3 and A2 follow-on runs (empty, awaiting runs)
```

Aggregator now rejects bare `results_backup/` with an actionable error pointing at cohort roots.

Updated: `analysis_inputs/reviewer_ablation_gold.csv`, `analysis_inputs/concentration_annotations.csv` (all run_dir paths), `docs/commands.md`, `docs/handoff_final_push_expansion.md`.

### Rerun output workflow

When corrective reruns complete:
1. Raw outputs go to `results/final_rerun_*` then are copied to `results_backup/rerun_raw/final_rerun_*`.
2. Assemble the paper-ready cohort in `results_backup/final_corrected/` by copying clean runs from `final_historical/` and substituting corrected runs from `rerun_raw/`.
3. Run `uv run python -m analysis.aggregate --root results_backup/final_corrected --out analysis_outputs/final_corrected`.
4. Paper claims cite `final_corrected` outputs only.
