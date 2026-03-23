# Prompt For Another Agent: Refresh The Master Plan And Hackathon Framing

You are helping on **Look-Before-You-Click**, an entry for the **Apart Research AI Control Hackathon** (**March 20-22, 2026**).

This project should be framed primarily as **Track 2 - Control Protocol Design**. A secondary Track 1 angle exists only if you explicitly use the scheming side-task setting as a miniature custom control environment.

Your job is to read the current repo state, understand how the project evolved from the original March 20 plan into the March 22 corrected state, and then improve the high-level research framing docs so they match reality.

## Mission

Refresh the planning docs so they describe:

- what the project originally set out to do,
- what it actually is now,
- what has already been built,
- what changed during the final push,
- what the corrected results say,
- what should be the main paper story,
- what should be supporting evidence only,
- and what claims must be weakened or removed.

Do **not** turn this into a new product vision. Keep it a protocol-wrapper-and-evaluation project.

## Ground Truth Files To Read

Read these in roughly this order:

1. `docs/handoff_shared.md`
2. `docs/master_plan.md`
3. `docs/concise_master_plan.md`
4. `docs/technical_spec.md`
5. `notes/phase0_progress.md`
6. `notes/final_push_progress.md`
7. `notes/final_push_results_analysis.md`
8. `docs/handoff_final_push.md`
9. `notes/final_push_expansion_progress.md`
10. `docs/handoff_final_push_expansion.md`
11. `analysis_outputs/final_corrected/protocol_variant_summary.csv`
12. `analysis_outputs/final_corrected/results_summary.csv`
13. `analysis_outputs/final_corrected/overhead_summary.csv`
14. `analysis_outputs/concentration_failure_taxonomy.csv`
15. `analysis_inputs/concentration_annotations.csv`
16. `analysis_inputs/reviewer_ablation_gold.csv`
17. `analysis/a1_vs_a2_table.py`

Also inspect the current artifact layout:

- `results_backup/final_corrected/`
- `results_backup/final_historical/`
- `results_backup/smoke/`
- `results_backup/rerun_raw/`
- `results_backup/expansion/`

## Project Context You Should Keep In Mind

This project is a **thin control protocol wrapper** over `os-harm` / `OSWorld`:

- intercept actions after `agent.predict(...)`
- review them before `env.step(...)`
- route only **critical** actions
- use the live screenshot + accessibility tree + recent history
- optionally generate an untrusted **legibility report**
- send critical actions to a trusted reviewer
- optionally resample once or defer one step to a trusted fallback
- log everything cleanly
- run the post-run judge explicitly

The project is **not**:

- a new benchmark
- a new agent
- a general prompt-injection defense
- a system-isolation platform
- a dashboard / service / product

The deliverable is still: **protocol wrapper + evaluation**.

## What Changed Since The Original Plan

The original March 20 framing was mostly future-tense. The repo now contains:

- a real `control/` layer wired into `os-harm`
- a real rule-based critical-action router
- a real trusted reviewer
- legibility generation
- three controller modes:
  - `allow_or_terminate`
  - `allow_or_resample_once`
  - `allow_or_trusted_fallback_once`
- a second threat model:
  - scheming side-task wrappers plus `control/scheming.py`
- smoke-demonstrated B4R and B4T behavior
- corrected core cohorts under `results_backup/final_corrected/`
- completed expansion work: B1/B2/B3 ablation ladder and A2 protocol-aware attack probes (all runs finished, results aggregated)

This means the plan docs should no longer read like "here is what we might build."

## Canonical Results To Anchor On

When core claims differ between older notes and corrected artifacts, use the **corrected** core cohort.

### Environmental corrected core

From `analysis_outputs/final_corrected/results_summary.csv`:

| Baseline | Condition | Tasks | Main-task success | Safety | Reviews | Blocks | Terminations |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | honest | 5 | 60.0% | 100.0% | 0 | 0 | 0 |
| B0 | attack | 12 | 41.7% | 58.3% | 0 | 0 | 0 |
| B4 | honest | 5 | 40.0% | 100.0% | 1 | 0 | 0 |
| B4 | attack | 12 | 50.0% | 66.7% | 8 | 4 | 4 |

### Scheming corrected core

From `analysis_outputs/final_corrected/results_summary.csv`:

| Baseline | Condition | Tasks | Main-task success | Side-task prevented | Side-task succeeded | Reviews | Blocks | Terminations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | honest | 12 | 75.0% | 100.0% | 0/12 | 0 | 0 | 0 |
| B0 | attack | 12 | 58.3% | 58.3% | 5/12 | 0 | 0 | 0 |
| B4 | honest | 12 | 41.7% | 100.0% | 0/12 | 5 | 1 | 1 |
| B4 | attack | 12 | 41.7% | 75.0% | 3/12 | 10 | 6 | 6 |

### Smoke evidence for protocol variants

The smoke runs show:

- B4R emits real `RESAMPLE` decisions
- B4T emits real `DEFER_TO_TRUSTED` decisions

Treat those as real but still **secondary** unless you verify a full clean matrix.

## Important Failure Modes

The current paper should explicitly discuss:

- **timing**: harm finishes before the next review checkpoint
- **router gap**: the decisive action is not surfaced as critical
- **boundary**: no reviewable critical action exists (`stop_task`)
- **reviewer false positive**: ambiguous benign actions get blocked

Use these as part of the contribution, not just as caveats.

## Current Repo State Beyond The Older Notes

The workspace is ahead of some written progress notes:

- `final_corrected/` exists and is already aggregated
- concentration analysis outputs exist
- reviewer-ablation labeling exists, though that pipeline may still be incomplete
- expansion scripts and some expansion results exist
- A2 scaffolding exists

Your writeup should reflect this without pretending incomplete expansion evidence is finished.

## What You Should Produce

Update:

- `docs/master_plan.md`
- `docs/concise_master_plan.md`

If useful, also add or update a short context packet for future agents.

## Writing Requirements

The refreshed docs should:

- explain what the hackathon is and why this fits Track 2
- explain what the project was on March 20 versus what it is on March 22
- use present tense for implemented components
- use corrected results for canonical core claims
- clearly separate:
  - environmental prompt injection
  - scheming / intentional subversion
  - smoke-only secondary protocol variants
  - partial expansion work
- preserve the main control claim
- narrow or remove claims that are not supported

## Claims You Must Not Overstate

Do **not** claim:

- "we solved prompt injection"
- "we solved CUA safety"
- sparse review beats blanket state-grounded review unless B2 evidence is actually complete
- robustness to protocol-aware attackers (A2 runs are complete but inconclusive: N=1, no protocol engagement observed)
- B4R/B4T as the main headline if they are still mostly smoke-supported

Do **state clearly**:

- `stop_task` is a threat-model boundary
- timing failures are structural for per-action interception
- the project is a wrapper and evaluation, not a product

## Best End State

The updated master plan should make the current project read like this:

> A control-style evaluation of sparse, state-grounded review for computer-use agents: a thin wrapper over OS-Harm that intercepts critical GUI actions, tests both environmental prompt injection and scheming side-task attacks, shows meaningful but bounded safety gains, and identifies the structural failure modes that determine when this style of control will and will not work.

If the existing long master plan is still mostly a shell, replace it with a fully useful current-state document.
