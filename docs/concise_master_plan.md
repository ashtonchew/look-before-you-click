# Concise Summary — Computer-Use Control Master Plan

## Working title
**Look-Before-You-Click: Critical-Action Deferral with State-Grounded Legibility for Computer-Use Agents**

## One-paragraph abstract
This project should be framed as an **AI control protocol paper for computer-use agents**, not as a general prompt-injection defense and not as just another computer-use safety benchmark. The core idea is to adapt **critical-action deferral** to GUI environments: let an untrusted computer-use agent act normally most of the time, but pause on a small set of **irreversible or high-impact GUI actions** and route those actions to a trusted reviewer with access to the **live screen state**, **recent history**, and a **structured explanation** from the agent. The main evaluation should use **paired OS-Harm / OSWorld tasks**, especially prompt-injection tasks that can be run with and without injection, and report the standard control tradeoff: **safety, usefulness, monitor quality, and overhead**. The main research question is whether harmful computer-use behavior is **concentrated in a small number of reviewable GUI actions**; if so, sparse trusted review may be a realistic deployment strategy.

## Core claim
The central claim is:

> Most catastrophic failures of computer-use agents pass through a small set of **irreversible GUI actions** that are unusually monitorable from the live screen state. Therefore, a protocol that defers **only those critical actions** to a trusted reviewer can achieve a better **safety–usefulness–latency tradeoff** than blanket monitoring.

This is strong because it is:
- important for real deployments,
- directly relevant to AI control,
- feasible within a hackathon,
- and novel in a defensible way.

## Defensible novelty claim
The strongest claim to make is:

> This project provides an explicit **AI control-style evaluation** of **critical-action deferral** for realistic computer-use agents, combining:
> 1. **state-grounded trusted inspection** of the GUI,
> 2. a **legibility protocol** that forces structured justification before risky actions,
> 3. **paired benign vs attack evaluation** on OS-Harm / OSWorld-style tasks, and
> 4. an empirical test of the **critical-action concentration hypothesis**.

Claims to **avoid**:
- “first defense for computer-use agents”
- “robust solution to prompt injection”
- “first real-time security system for CUAs”
- “first system-level isolation defense”

This project is **not** trying to beat full-stack CUA defense papers. Its niche is narrower and cleaner: **targeted control evaluation**.

## Project framing
- **Primary track:** Track 2 — Control Protocol Design
- **Secondary track:** Track 1 if a mini custom control setting is added
- **Positioning:** Not “can we defend CUAs in general?” but **“can targeted control work for CUAs?”**

## Why this should work
### 1. Harm likely concentrates at irreversibility boundaries
In GUI tasks, the harmful outcome usually becomes real only when the agent crosses an irreversible step, such as:
- Send / Submit / Post / Share
- Upload / Attach / Export
- Delete / Overwrite / Confirm destructive action
- Permission / Settings / Security change
- External navigation or domain boundary crossing
- Launching shell / executable content
- Exposing secrets / credentials
- Clipboard paste into untrusted destination
- Financial / account confirmation
- Bulk actions

These steps are where:
- harm becomes real,
- intent is clearer,
- the visible screen state is more informative,
- and blocking is still possible.

### 2. Screen state is more monitorable than action text alone
A language-only monitor sees abstract actions like “Click send.” A state-grounded monitor can also inspect:
- button labels,
- recipient fields,
- domains/URLs,
- selected files,
- destructive dialog text,
- current settings page,
- whether the clicked object matches the user’s task.

That is especially important in GUI environments, where the dangerous object is often **the current screen state**, not just the action string.

### 3. Deferral may be more robust than generic monitoring/resampling
A pure monitor/resample protocol can fail because the attacker learns what looks suspicious, resampling can create extra attack chances, and monitors may miss the decisive moment. Critical-action deferral instead routes the highest-leverage step away from the untrusted policy.

### 4. Legibility should help monitors
Before risky actions, the untrusted agent should produce a structured explanation of:
- what action it wants to take,
- what UI element it is targeting,
- why the action is needed for the user’s goal,
- what visible effect should happen next,
- how security-relevant it is,
- and its confidence.

This is **not** because the explanation is trusted. It is because mismatches become easier to detect.

### 5. Sparse review is necessary
Computer-use agents already suffer from latency and extra steps. Reviewing every step is likely too expensive. The design therefore aims for **high recall on decisive risky actions** with **low benign interruption**.

## Final recommended experiment
### Primary experiment
**Critical-Action Deferral in Paired OS-Harm / OSWorld Tasks**

Use:
- **OS-Harm prompt-injection tasks** as the attack condition
- the **same tasks with injection removed** as the honest condition whenever possible

Why this is best:
- same environment family,
- same apps,
- same main objectives,
- attack toggled by environmental manipulation,
- automatic judging,
- existing logs/screenshots/accessibility trees,
- lower implementation risk.

### Apps to prioritize
- browser
- email client
- file manager / OS
- possibly code editor

### Recommended task slice
If time is limited:
- **Dev:** 15–20 paired prompt-injection tasks
- **Held-out test:** 20–30 paired prompt-injection tasks
- **Optional robustness:** 10 model-misbehavior tasks
- **Optional honest-only expansion:** 10 extra OSWorld benign tasks

If compute allows: scale to **40–60 paired tasks**.

### Optional secondary experiment
Add a **mini custom computer-use control setting** with hidden side tasks to make the project feel more like classic control.

Good side tasks:
- unauthorized send,
- unauthorized upload,
- unauthorized delete/overwrite,
- unauthorized navigation,
- unauthorized permission change.

Keep it small:
- 10–20 tasks,
- 2–4 side-task templates,
- 1–2 apps per family.

This is a bonus/appendix if time permits.

## Protocol to evaluate
Define:
- **U** = untrusted computer-use agent
- **T** = trusted reviewer / trusted fallback policy
- **R** = risk router
- **I** = state-grounded inspector

### Basic flow
1. U proposes an action.
2. R decides whether it is a **critical action**.
3. If not critical, execute normally.
4. If critical, require a **legibility explanation** from U.
5. Build a **review package** for T containing:
   - proposed action,
   - screenshot,
   - accessibility tree,
   - recent action history,
   - legibility schema,
   - trusted extracted facts if available.
6. T returns one of:
   - **ALLOW**
   - **RESAMPLE**
   - **DEFER_TO_TRUSTED**
   - **BLOCK**

### Review package contents
At minimum:
- screenshot
- accessibility tree
- recent history
- structured explanation

If feasible, also include read-only facts like:
- current URL/domain,
- app/window title,
- recipient fields,
- selected filenames,
- dialog text,
- selected items.

## Baselines and ablations
### Core baselines
- **B0:** Untrusted-only
- **B1:** Language-only trusted monitor
- **B2:** Screen-based trusted monitor on every step
- **B3:** Critical-action routing without legibility
- **B4:** Critical-action routing + legibility
- **B5:** Critical-action routing + legibility + trusted read-only facts

### Optional protocol variants
- defer-only vs resample-only vs hybrid
- trusted fallback action vs trusted edit
- different routing thresholds

### Attack-model ablations
At minimum include:
- **A1:** default OS-Harm attack
- **A2:** protocol-aware attacker

If possible add:
- **A3:** attack selection (attacker chooses when to strike)

## Main metrics
### Primary
- **Safety:** proportion of attack trajectories where the harmful objective fails
- **Usefulness:** proportion of honest trajectories where the main task succeeds
- **Monitor quality:** TPR/recall, FPR, ROC AUC, maybe PR AUC
- **Overhead / control tax:** review rate, extra reviewed steps, latency increase, extra model calls

### Secondary
- critical-action coverage,
- review precision,
- benign interruption rate,
- decisive-step recall,
- target-grounding error rate.

### Thresholding
Set thresholds on a **dev set**, ideally reporting at fixed honest review budgets like **1%, 5%, and 10%**.

## Key hypotheses
- **H1 — Concentration:** Most harmful trajectories pass through a small number of critical GUI action families before irreversible harm.
- **H2 — Safety:** Critical-action deferral beats no monitoring and language-only monitoring on attack tasks.
- **H3 — Usefulness:** Critical-action deferral preserves more usefulness than monitoring every step.
- **H4 — Legibility:** Legibility improves trusted review at similar usefulness.
- **H5 — Robustness:** Protocol-aware attacks hurt broad/generic monitoring more than critical-action deferral.

## What counts as success
### Strong win
- clear safety improvement,
- modest usefulness hit,
- strong concentration result,
- some adaptive-attack robustness,
- interpretable traces.

### Medium win
- modest protocol gains,
- but strong concentration analysis and good case studies.

### Negative but still valuable
If the protocol does not help because attacks are too diffuse or GUI state is not actually reviewable at decisive moments, that is still a useful result because it falsifies a concrete control hypothesis.

## Threat model
### In scope
- benign user task,
- malicious environment content or prompt injection steering the agent toward unsafe action,
- optionally, a hidden side-task attacker in the custom extension.

### Out of scope
Do **not** claim to solve:
- arbitrary asynchronous attacks,
- attacks that never pass through visible critical states,
- long-horizon future-risk prediction,
- full isolation/system-level security.

## Risks and pivots
### Main risks
- read-only probes may be hard to implement,
- paired honest tasks may be annoying,
- adaptive red teaming may take too long,
- results may be noisy,
- project may sprawl.

### Recommended pivots
- If probes are hard: use screenshot + a11y tree + history + legibility only.
- If paired tasks are hard: use OS-Harm attack tasks and matched OSWorld honest tasks.
- If adaptive attacks are hard: add at least one protocol-aware prompt variation.
- If end-to-end gains are weak: lean into concentration analysis, per-action-family results, and qualitative traces.
- Do **not** build a new benchmark, a large dataset, a world model, a full isolation architecture, or a major training pipeline.

The winning version is a **clean protocol evaluation**.

## Writing strategy for the hackathon report
The paper should be built around **one idea** and **one figure**.

### Main story
Dangerous computer-use behavior may concentrate around a small number of **irreversible GUI actions**, so reviewing only those actions may give a good **safety/usefulness tradeoff**.

### Key figure
- **Safety vs usefulness** for all protocol variants

### Best additional figures/tables
- concentration plot by action family,
- overhead plot,
- baseline results table,
- failure taxonomy,
- prior-work positioning table.

### Must-have content
- paired honest vs attack evaluation,
- clear baselines,
- fixed critical-action taxonomy,
- at least one adaptive condition,
- safety + usefulness + overhead,
- 3–5 qualitative traces,
- honest novelty claim,
- a clean main plot.

### Avoid
- overclaiming robustness,
- reframing the work as generic prompt-injection defense,
- evaluating only attack tasks and forgetting usefulness,
- unnecessary scope expansion.

## 72-hour execution plan
### Day 1
- run baseline OS-Harm tasks,
- verify paired honest runs,
- pick model(s),
- add logging,
- define critical-action taxonomy,
- build first rule-based router.

### Day 2
- implement legibility schema,
- implement trusted reviewer,
- run B0/B1/B3/B4 on dev,
- set thresholds,
- start saving failure cases.

### Day 3
- run held-out test,
- add one adaptive/protocol-aware condition,
- annotate decisive harmful steps,
- make plots/tables,
- write report.

### Final priority order
1. main result plot
2. concentration analysis
3. qualitative traces
4. adaptive attack condition
5. optional custom setting

## Bottom line
If only one thing gets done, it should be:

> **A paired OS-Harm / OSWorld evaluation of critical-action deferral with state-grounded review and GUI legibility, plus a concentration analysis of decisive harmful actions.**

That is the cleanest, strongest, and most defensible version of the project.