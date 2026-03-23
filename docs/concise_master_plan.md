# Concise Master Plan — Look-Before-You-Click

## Working title
**Look-Before-You-Click: Critical-Action Review for Computer-Use Agents**

## Hackathon context
- **Event:** Apart Research AI Control Hackathon, March 20-22, 2026
- **Best fit:** Track 2 - Control Protocol Design
- **Possible secondary fit:** Track 1 only if the scheming side-task setting is framed as a small custom control environment
- **Submission type:** protocol wrapper + evaluation, not a new benchmark or new agent

## One-paragraph abstract
This project is an **AI control protocol evaluation for computer-use agents**. We wrap the existing OS-Harm agent loop with a thin controller that intercepts proposed GUI actions before execution, routes only **critical actions** to a trusted reviewer, and gives that reviewer the **live screen state**, **accessibility tree**, **recent history**, and an optional **legibility report** from the untrusted agent. The main question is whether harmful computer-use behavior is concentrated in a small number of reviewable GUI actions. If so, sparse state-grounded review may improve safety without paying the full usefulness and latency cost of blanket monitoring.

## What the project is now
This is no longer just a proposal. As of **March 22, 2026**, the repo contains:

- a working control seam between `agent.predict(...)` and `env.step(...)`
- a rule-based critical-action router
- state-grounded and language-only reviewer modes
- legibility generation
- three controller modes:
  - `allow_or_terminate`
  - `allow_or_resample_once`
  - `allow_or_trusted_fallback_once`
- a scheming side-task threat model with a side-task judge
- corrected core results under `results_backup/final_corrected/`
- completed environmental ablation ladder (B0-B4) under `analysis_outputs/ablation_ladder/`
- completed A2 adaptive attacker runs (3 variants x B0/B4, inconclusive) under `results_backup/expansion/`
- concentration / failure-taxonomy outputs with concrete counts

## Core claim
The main claim should stay:

> Harmful computer-use trajectories often bottleneck through a small set of high-impact GUI actions that are unusually monitorable from the live screen state. Reviewing only those actions can improve safety while preserving more usefulness than broad monitoring would in practice.

## What changed from the original plan
The original March 20 plan was future-tense. The project now has:

- real implementation instead of just design sketches
- smoke-demonstrated B4R and B4T variants
- a second threat model, so the work reads as AI control rather than only prompt-injection defense
- a correction layer for router precision, scheming substrate validity, and cohort-safe aggregation
- a stronger failure-taxonomy story than the original plan anticipated

## Canonical evidence to use
Use the **corrected** cohort, not the older historical note, for paper-safe core claims.

### Environmental threat model

| Baseline | Condition | Tasks | Main-task success | Safety | Reviews | Blocks |
|---|---:|---:|---:|---:|---:|---:|
| B0 | honest | 5 | 60.0% | 100.0% | 0 | 0 |
| B0 | attack | 12 | 41.7% | 58.3% | 0 | 0 |
| B4 | honest | 5 | 40.0% | 100.0% | 1 | 0 |
| B4 | attack | 12 | 50.0% | 66.7% | 8 | 4 |

Headline: **B4 improves environmental safety from 58.3% to 66.7% with zero false-positive blocks on the honest slice.**

### Scheming threat model

| Baseline | Condition | Tasks | Main-task success | Side-task prevented | Side-task succeeded | Reviews | Blocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | honest | 12 | 75.0% | 100.0% | 0/12 | 0 | 0 |
| B0 | attack | 12 | 58.3% | 58.3% | 5/12 | 0 | 0 |
| B4 | honest | 12 | 41.7% | 100.0% | 0/12 | 5 | 1 |
| B4 | attack | 12 | 41.7% | 75.0% | 3/12 | 10 | 6 |

Headline: **B4 improves scheming side-task prevention from 58.3% to 75.0%, but still pays usefulness and calibration cost.**

### Secondary protocol evidence

Smoke runs already show:

- B4R emits real `RESAMPLE` decisions
- B4T emits real `DEFER_TO_TRUSTED` decisions

These are valuable secondary results, but not yet the main empirical headline.

### Ablation ladder (environmental, completed)

Source: `analysis_outputs/ablation_ladder/ablation_ladder_metrics.csv`

| Baseline | Usefulness | Safety | Source cohort |
|---|---|---|---|
| B0 Unmonitored | 60.0% | 58.3% | final_corrected |
| B1 Full Review, Text-Only | 0.0% | 83.3% | expansion |
| B2 Full Review, Visual | 40.0% | 100.0% | expansion |
| B3 Selective | 60.0% | 91.7% | expansion |
| B4 Selective, Justified | 40.0% | 66.7% | final_corrected |

Key finding: B3 Selective achieves the best safety/usefulness tradeoff. B4 Selective, Justified is surprisingly lower than B3 on both axes.

Caveats: B0/B4 from `final_corrected`, B1/B2/B3 from `expansion` (same tasks, different run session). N=5 benign, 12 attack per baseline. The B3 > B4 result may reflect cross-cohort variation, small sample noise, or legibility introducing reviewer confusion.

### A2 adaptive attacker (completed, inconclusive)

Source: `analysis_outputs/a1_vs_a2_comparison.csv`

All 6 A2 runs finished. No A2 variant produced a case where the protocol actively intercepted an adaptive attack:

- A2-env-1 (reframed exfil): agent didn't follow adversarial instructions
- A2-env-2 (reviewer-aware URL): B0 unsafe, B4 safe -- but with zero protocol reviews (agent avoided attack on its own)
- A2-schem-1 (protocol-aware scheming): agent didn't follow protocol-aware prompt

Appendix-only. Do not claim adaptive robustness.

### Failure taxonomy (concrete counts)

Source: `analysis_outputs/concentration_failure_taxonomy.csv`

| Failure mode | Outcome | Count | Threat model |
|---|---|---|---|
| unspecified | harm_blocked | 18 | environmental |
| timing | harm_succeeded | 8 | scheming |
| unspecified | harm_blocked | 5 | scheming |
| unspecified | harm_succeeded | 4 | environmental |
| reviewer_false_positive | harm_blocked | 4 | scheming |
| boundary | harm_succeeded | 3 | environmental |
| unspecified | attack_abandoned | 3 | environmental |
| router_gap | harm_succeeded | 2 | scheming |

Timing failures are concentrated in scheming (8/8). Router gaps are scheming-only (2/2). Boundary failures are environmental-only (3/3, `stop_task` pattern).

## Honest boundaries
The paper should state these clearly:

- `stop_task`-style attacks are outside the protocol's intervention boundary if no critical action is emitted.
- Timing failures are structural when harm completes before the next review checkpoint.
- Sparse review only works if the router surfaces the decisive action correctly.
- B2 evidence is complete: blanket review (B2) achieves 100% safety at 40% usefulness. Sparse routing (B3) achieves 91.7% safety at 60% usefulness. Claim tradeoff advantage, not absolute safety advantage.
- A2 runs are complete but inconclusive (N=1, no protocol engagement observed). Do not claim robustness to protocol-aware attackers.
- The B3 > B4 finding (legibility appears to hurt) is preliminary. Report it with cross-cohort and sample-size caveats. Do not claim legibility helps the reviewer.

## Failure taxonomy
The current failure story is already strong enough to matter:

- **timing**: harm completes before the next review checkpoint
- **router gap**: the critical action is not surfaced correctly
- **boundary**: no reviewable critical action exists
- **reviewer false positive**: the reviewer blocks an ambiguous but benign action

This should be in the main paper, not buried in limitations.

## What to emphasize in the paper
- Main figure: corrected environmental **safety vs usefulness**
- Second figure: **concentration / failure taxonomy**
- Third figure candidate: **ablation ladder** (5-baseline environmental frontier)
- Supporting table: corrected scheming results
- B3 > B4 finding with cross-cohort caveats as a discussion point
- Supporting qualitative traces:
  - caught-and-blocked
  - reviewer discrimination
  - timing failure
  - router gap
  - `stop_task` boundary
  - optionally one B4R retry trace and one B4T fallback trace

## What not to emphasize
- generic prompt-injection defense
- "we solved computer-use safety"
- A2 results (complete but inconclusive -- appendix only)
- sparse beats blanket on raw safety (B2 is safest; claim tradeoff advantage instead)
- building more infrastructure

## Current expansion state
All expansion runs completed March 22, 2026. Artifacts:

- `results_backup/expansion/` -- 12 expansion run directories (6 B1/B2/B3 ablation + 6 A2 adaptive)
- `analysis_outputs/ablation_ladder/ablation_ladder_metrics.csv` -- merged B0-B4 environmental ladder
- `analysis_outputs/a1_vs_a2_comparison.csv` -- 12-row A1-vs-A2 comparison

**Framing:**
- `results_backup/final_corrected/` remains canonical for core paper claims.
- The **ablation ladder** is the expansion's primary contribution to the paper. It provides the full B0-B4 environmental frontier and reveals the B3 > B4 anomaly. It belongs in the main paper or a prominent appendix.
- **A2 results** are strictly appendix material (N=1, no protocol engagement observed).
- `results_backup/expansion/` is a mixed storage bucket; `analysis_outputs/ablation_ladder/` is the coherent cross-cohort product.

## Immediate priority order
1. Keep `final_corrected` as the canonical core-results cohort.
2. Use environmental B0 vs B4 as the main headline.
3. Use scheming B0 vs B4 as the control-framing result.
4. Use B4R/B4T as smoke-demonstrated secondary variants.
5. Use the failure taxonomy as a contribution, not just a caveat.
6. Use the ablation ladder as a main supporting figure.
7. Report the B3 > B4 finding with cross-cohort and sample-size caveats.
8. Describe A2 briefly in an appendix as an honest null result.
9. Obtain reviewer ablation gold labels (10-20 rows) and concentration annotations (20-30 rows) if time allows.

## Bottom line
The cleanest current description is:

> **A thin control wrapper over OS-Harm that reviews only critical GUI actions, evaluates both prompt-injection and scheming threat models, and shows that sparse state-grounded review can help, but only within a clear and interpretable boundary set by timing, routing, and reviewer calibration.**

The completed ablation ladder adds:

> **The five-baseline environmental frontier reveals that sparse routing without legibility (B3) achieves the best safety/usefulness tradeoff, while adding legibility (B4) unexpectedly degrades performance -- a preliminary finding reported with cross-cohort and sample-size caveats.**
