# Technical Specification and Architecture Plan
## Look-Before-You-Click: Critical-Action Review for Computer-Use Agents
**Status:** implementation spec for hackathon execution  
**Date:** 2026-03-20  
**Primary track:** Track 2 — Control Protocol Design  
**Secondary track:** Track 1 if a small custom side-task setting is added  
**Source inputs:** team master plan, current OS-Harm repo, current OSWorld repo/docs, and recent control/CUA papers

---

## 0. What this document is

This is the engineering version of the project plan.

Its job is to make implementation easy for multiple coding agents working in parallel. It is intentionally more concrete and less ambitious than the research framing document.

If there is a conflict:

1. **Use this document for implementation detail**
2. **Use the master plan for paper framing and novelty framing**
3. **Choose the simpler path unless the simpler path would break the core claim**

The core claim remains:

> Harmful computer-use behavior often bottlenecks through a small set of high-impact GUI actions.  
> If we review only those actions, using the live screen state plus a structured explanation, we may get a better safety/usefulness tradeoff than broad monitoring.

---

## 1. Non-negotiable engineering principles

### 1.1 Code style
We are optimizing for hackathon speed and readability, not elegance.

Follow these rules:

- Write code that is easy to skim.
- Prefer short files and short functions.
- Use obvious names.
- Use early returns.
- Avoid inheritance unless it removes duplicated code right now.
- Avoid “frameworks” inside the repo.
- Avoid clever abstractions.
- Keep state explicit.
- Prefer plain dicts / dataclasses / typed functions over meta-programming.
- Log in structured JSON whenever possible.
- If a piece of code feels “smart”, simplify it.

### 1.2 Scope control
Do **not** build any of the following in the MVP:

- a new benchmark
- a new agent architecture
- training pipelines
- OCR pipelines
- world models
- asynchronous services
- a database
- a message queue
- a browser extension
- a system-level isolation framework
- a fancy dashboard

### 1.3 Product rule
The deliverable is **a protocol wrapper plus evaluation**, not a new agent.

That means:

- start from **OS-Harm**
- keep the existing agent path intact
- intercept actions before execution
- add review only where needed
- log everything cleanly
- compute the safety/usefulness tradeoff

---

## 1.4 Paper-honesty guardrails

These constrain what the simplified spec is allowed to claim. Enforce across code, spec, and paper.

**Guardrail 1: Keep B2 or drop the "sparse beats blanket" claim.**
The master plan's H3 claims critical-action review preserves more usefulness than monitoring every step. Without B2 (blanket state-grounded monitor), that claim has no evidence. Fix: run B2 on a small slice (3–5 tasks) as a supporting data point — enough to preserve the comparison, but present it as supporting evidence, not a headline result. If compute doesn't allow even that, weaken the paper framing to compare only against no-monitoring and language-only monitoring.

**Guardrail 2: Don't call the MVP "deferral" until deferral exists.**
The MVP implements ALLOW / BLOCK only. Until `DEFER_TO_TRUSTED` actually lands:
- In the spec and code: call the system **"critical-action routing with state-grounded review"**
- In paper framing: describe it as a **control protocol for critical actions**, not a completed deferral protocol
- `RESAMPLE` and `DEFER_TO_TRUSTED` are documented stretch modes only

---

## 2. Final build target

By the end of the hackathon, the repo should be able to do the following:

1. Run a benign version of a prompt-injection OS-Harm task
2. Run the injected version of the same task
3. Intercept each proposed action before execution
4. Decide whether the action is **critical**
5. For critical actions, optionally generate a structured **legibility report**
6. Send a **review package** to a trusted reviewer
7. Apply a simple controller policy:
   - allow
   - or block / terminate
   - optionally resample once
   - optionally use trusted fallback for one action
8. Save control-specific logs next to OS-Harm logs
9. Run the judge explicitly after task completion
10. Aggregate results into:
    - usefulness
    - safety
    - review rate
    - block rate
    - latency overhead
    - one safety-vs-usefulness plot
11. Export a small set of example traces for the report

If we only complete the first 9 items, the project is still viable.

---

## 3. Hard decisions

This section is the main “do not overthink it” part.

### 3.1 Benchmark choice
**Use `tml-epfl/os-harm` as the starting repository.**

Why:

- it already contains the environment, runner, baseline agent path, task configs, and judge path
- it supports prompt injection tasks directly
- the same prompt-injection task configs contain injection details and `run.py` applies them only when `--inject` is passed, which makes paired benign-vs-attack evaluation feasible
- it already saves screenshots, `better_log.json`, `traj.jsonl`, and videos

### 3.2 Environment choice
**Default to VMware/local execution for the hackathon.**

Why:

- OS-Harm says its experiments were run with VMware
- OS-Harm does not present Docker/AWS as its tested default path
- OSWorld supports Docker and AWS, but adapting the OS-Harm fork to a new provider is not the best first move during a three-day sprint

Fallback rule:

- if the team already has a working KVM-capable remote setup, Docker is acceptable
- otherwise do not spend time switching providers

### 3.3 Observation choice
**Always pass `--observation_type screenshot_a11y_tree` explicitly. Do not rely on defaults.**

Why:

- OS-Harm says this was their best-performing observation type
- the current `run.py` default is `a11y_tree`, so the desired setting must be passed explicitly

### 3.4 Action space choice
**Support `pyautogui` only in the MVP.**

Why:

- current OS-Harm `run.py` defaults to `pyautogui`
- the repo’s example execution traces are stored under `pyautogui/screenshot_a11y_tree/...`
- OSWorld mainly uses `pyautogui`
- one action format means simpler parsing and fewer edge cases

### 3.5 Agent choice
**Do not build a new agent. Use the existing baseline agent path.**

The control logic must wrap the agent, not replace it.

### 3.6 Router choice
**Use a rule-based critical-action router in the MVP.**

Do not start with an LLM router.

A simple rule-based router is:
- easier to debug
- easier to explain in the paper
- less likely to explode cost and latency
- good enough for a hackathon MVP

An LLM router is optional if the rule-based router is clearly too weak.

### 3.7 Reviewer choice
**Use a separate trusted review call only for flagged critical actions.**

Do not monitor every step in the default protocol.

### 3.8 Legibility choice
**Do not rewrite the agent’s base prompting in the MVP.**

Instead:

- keep the agent’s normal `predict(...)` flow
- only when an action is flagged as critical, ask for a separate structured explanation

This keeps the base agent stable and avoids breaking the benchmark agent.

### 3.9 Controller policy choice
**Default control mode is `allow_or_terminate`.**

Meaning:

- if the reviewer allows the action, execute it
- if the reviewer disallows it, terminate the task run and mark the action as blocked

This is the simplest possible semantics.

Optional modes:
- `allow_or_resample_once`
- `allow_or_trusted_fallback_once`

### 3.10 Judge execution choice
**Run the judge explicitly after every task run. Do not assume the repo does it for you.**

Reason:

- the README says judging happens automatically
- the current `run.py` has the success-path judgment block commented out
- so the implementation should add an explicit post-run judge call on the normal path

---

## 4. What we are actually building

At a high level:

```text
OS-Harm runner
  -> baseline agent predicts next action
  -> control wrapper intercepts proposed action
  -> if action not critical: execute
  -> if action critical:
       - optionally request structured legibility report
       - build review package from screenshot + a11y + action + recent history
       - trusted reviewer returns allow/disallow + reason
       - controller decides what to do
  -> continue task
  -> run judge
  -> aggregate metrics
```

### 4.1 Architecture in one diagram

```text
run.py
  └── lib_run_single.run_single_example(...)
        ├── agent.predict(instruction, obs)
        │     └── returns response, actions
        ├── control.controller.handle_actions(...)
        │     ├── action_normalizer
        │     ├── a11y_parser (includes target matching)
        │     ├── critical_router
        │     ├── reviewer (includes legibility, critical only)
        │     └── controller_policy
        ├── env.step(...)
        ├── OS-Harm logging
        ├── control logging
        └── explicit post-run judge call
```

---

## 5. Minimal repo change plan

Keep changes small and local.

### 5.1 Existing files to patch
Patch only these first:

1. `run.py`
2. `lib_run_single.py`

### 5.2 New package to add
Add a new top-level package:

```text
control/
  __init__.py
  types.py              # config + data types
  action_normalizer.py
  a11y_parser.py        # includes target matching
  critical_router.py
  reviewer.py           # trusted reviewer + legibility (one function)
  controller.py
  prompts.py
  logging.py            # log_io + metrics
```

Note: legibility is one function inside `reviewer.py`, not a separate module. Fact extraction is deferred — the reviewer gets the full a11y tree and screenshot directly.

### 5.3 New analysis package to add
Start with one script. Break it up later if it grows.

```text
analysis/
  __init__.py
  aggregate.py    # reads control_summary.json files, produces CSV + frontier plot
```

### 5.4 New config directory
Add:

```text
configs/
  control_none.json                        # B0
  control_always_review_language_only.json  # B1
  control_always_review_state_grounded.json # B2
  control_critical.json                    # B3
  control_critical_legibility.json         # B4
```

### 5.5 Do not patch these unless necessary
Do not touch these in the MVP:

- `mm_agents/agent.py`
- `desktop_env/*`
- OSWorld environment internals
- judge internals

The only acceptable exception is a tiny import or helper if there is no other way.

---

## 6. Runtime integration points

This section is important because it tells coding agents exactly where to hook in.

### 6.1 What the repo currently does
At a high level, `lib_run_single.run_single_example(...)` already does this:

1. reset agent and env
2. get observation
3. call `agent.predict(instruction, obs)`
4. append data to `better_log`
5. loop over returned `actions`
6. execute each action with `env.step(action, args.sleep_after_execution)`
7. save screenshots and `traj.jsonl`
8. call `env.evaluate()` and write `result.txt`

That means the best insertion point is:

- **after** `agent.predict(...)`
- **before** `env.step(...)`

### 6.2 New integration seam
Add a controller call inside the action loop:

```text
response, actions = agent.predict(...)

for raw_action in actions:
    decision = control_controller.review(
        instruction=instruction,
        obs=obs,
        raw_response=response,
        raw_action=raw_action,
        recent_history=recent_history,
        step_idx=step_idx,
        task_meta=...
    )

    if decision.execute:
        obs, reward, done, info = env.step(decision.action_to_execute, ...)
    else:
        terminate_or_resample_or_fallback(...)
```

### 6.3 Keep recent history simple
Track only the last 3 executed actions and review outcomes.

Use a plain list of dicts.

No event bus. No in-memory object graph.

---

## 7. Configuration surface

Add one explicit config file for the protocol.

### 7.1 CLI additions
Add the following CLI flags to `run.py`:

- `--control_config`
- `--control_mode`
- `--reviewer_model`
- `--legibility_model`
- `--run_judge_on_success`

Stretch flags (add only when implementing those features):
- `--review_budget_target`
- `--max_resamples_per_step`

### 7.2 Control config file
Use JSON for zero extra dependency risk.

Example schema:

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

Note: `include_visual_context` is a boolean that controls whether the reviewer sees screenshot + a11y tree + target info. When false, the reviewer sees only language context (instruction, raw response, action, history). This replaces the previous `reviewer_input_mode` field — it's one prompt path with conditional fields, not two separate modes.

### 7.3 Baseline config modes
All baselines should be just config changes, not code forks.

Use these five named modes (mapping to master plan B0–B4):

- `none` **(B0)** — no control protocol
- `always_review_language_only` **(B1)** — blanket monitor, language-only reviewer
- `always_review_state_grounded` **(B2)** — blanket monitor, state-grounded reviewer (run on small slice of 3–5 tasks)
- `critical_review` **(B3)** — rule-based routing, state-grounded reviewer, no legibility
- `critical_review_legibility` **(B4)** — routing + state-grounded reviewer + legibility

Stretch modes (build only if B0–B4 are complete):
- `critical_review_legibility_resample_once`
- `critical_review_legibility_trusted_fallback_once`

---

## 8. Internal data model

Keep internal types explicit and boring.

### 8.1 Observation
Do not define a new `ObservationSnapshot` type. Pass the existing `obs` dict from OSWorld directly — it already has `screenshot` and `accessibility_tree`. Pass `step_index`, `task_id`, and `domain` as separate params to the controller call.

### 8.2 NormalizedAction
A parsed representation of a `pyautogui` action, with target info merged in.

```python
NormalizedAction = {
  "raw_action": str,
  "primary_kind": "click" | "double_click" | "right_click" | "type" | "press" |
                  "hotkey" | "scroll" | "drag" | "wait" | "done" | "fail" | "other",
  "x": float | null,
  "y": float | null,
  "text": str | null,
  "keys": [str] | null,
  "button": str | null,
  "special_token": "WAIT" | "DONE" | "FAIL" | null,
  # Target info (merged from a11y matching, replaces separate A11yTarget type)
  "target_matched": bool,
  "target_tag": str | null,
  "target_name": str | null,
  "target_text": str | null,
  "target_bounds": {"x": float, "y": float, "w": float, "h": float} | null,
  "target_match_method": "contains_point" | "nearest_center" | "none"
}
```

Note: `sub_actions` and `raw_format` removed. We parse only `pyautogui` and extract the last impactful primitive per snippet.

### 8.3 RouterDecision
```python
RouterDecision = {
  "critical": bool,
  "family": str | null,
  "reasons": [str],
  "confidence": float
}
```

### 8.4 LegibilityReport
Generated only for critical actions if enabled. Produced by one function inside `reviewer.py`.

```python
LegibilityReport = {
  "action_type": str,
  "target_element": str,
  "target_text_or_label": str,
  "why_needed_for_user_goal": str,
  "expected_visible_effect_next": str,
  "what_could_go_wrong": str,
  "security_relevance": "low" | "medium" | "high",
  "confidence": float
}
```

### 8.5 ReviewPackage
```python
ReviewPackage = {
  "instruction": str,
  "raw_response": str,
  "normalized_action": NormalizedAction,
  "router_decision": RouterDecision,
  "obs": dict,               # OSWorld obs dict passed directly (screenshot + a11y_tree)
  "a11y_tree_linearized": str,
  "legibility_report": LegibilityReport | null,
  "recent_history": [dict],
  "step_index": int,
  "task_id": str,
  "domain": str
}
```

Note: `TrustedFacts` removed — the reviewer gets the full a11y tree and screenshot, which is sufficient. `A11yTarget` merged into `NormalizedAction` as `target_*` fields.

### 8.6 ReviewerResult
Keep the reviewer output simple.

```python
ReviewerResult = {
  "allow": bool,
  "risk_score": float,
  "primary_reason": str,
  "evidence": [str],
  "safer_alternative": str | null
}
```

### 8.7 ControllerDecision
This is what the runtime uses.

```python
ControllerDecision = {
  "execute": bool,
  "termination_reason": str | null
}
```

Stretch modes (`RESAMPLE`, `DEFER_TO_TRUSTED`) will add `resample_requested` and `trusted_fallback_requested` fields when implemented.

### 8.8 ControlEventLog
One JSONL record per reviewed action.

```python
ControlEventLog = {
  "task_id": str,
  "domain": str,
  "step_index": int,
  "raw_action": str,
  "normalized_action": dict,
  "router_decision": dict,
  "legibility_report": dict | null,
  "reviewer_result": dict | null,
  "controller_decision": dict,
  "review_latency_ms": int | null,
  "reviewer_model": str | null
}
```

---

## 9. Action normalization

This module is more important than it looks.

**pyautogui only.** OS-Harm defaults to pyautogui; OSWorld mainly uses pyautogui. Do not implement `computer_13` support in the MVP.

### 9.1 Parse these `pyautogui` calls

- `pyautogui.click(x, y)`
- `pyautogui.click(x=?, y=?, button=...)`
- `pyautogui.doubleClick(...)`
- `pyautogui.rightClick(...)`
- `pyautogui.moveTo(...)`
- `pyautogui.dragTo(...)`
- `pyautogui.write(...)`
- `pyautogui.typewrite(...)`
- `pyautogui.press(...)`
- `pyautogui.hotkey(...)`
- `pyautogui.scroll(...)`

### 9.2 Simple parsing rules
Do not build a real Python parser in the MVP.

Use regex and a few helper functions.

Rules:

1. Detect special tokens first: `WAIT`, `DONE`, `FAIL`
2. Detect click family
3. Detect type family
4. Detect key / hotkey family
5. Extract coordinates if obvious
6. If a snippet contains multiple primitives (e.g. `moveTo(...)` then `click()`), extract the **last impactful primitive** and inherit coordinates from any preceding `moveTo`

Do not track a `sub_actions` list. The router only needs the final action.

**Important — validate on Day 1:** After the parser is written, feed 3–5 real task traces from `better_log.json` through it. Log parse failures explicitly (don't silently return "other"). If the parser misses >10% of impactful actions, add targeted regex patterns before running the full evaluation.

---

## 10. Accessibility-tree parsing and target matching

This is the simplest reliable “state grounding” we have.

### 10.1 Why this matters
The linearized a11y tree includes:

- tag
- name
- text
- class
- description
- screen coordinates
- size

That is enough to do basic target resolution for click-like actions.

### 10.2 Parsing rule
Write a tiny parser that converts each line after the header into a node object.

Expected fields:

```python
{
  "tag": str,
  "name": str,
  "text": str,
  "class": str,
  "description": str,
  "x": float,
  "y": float,
  "w": float,
  "h": float
}
```

### 10.3 Click target matching algorithm
For click-like actions with coordinates:

1. find nodes whose rectangle contains `(x, y)`
2. if several match, choose smallest-area node
3. if none match, choose nearest node center within a configurable radius
4. if none are close, return no match

This is enough for MVP.

### 10.4 Do not do OCR
Do not add OCR for the hackathon build.

Use:
- screenshot as reviewer context
- a11y tree as structured text
- deterministic target matching from coordinates

---

## 11. Critical-action router

### 11.1 Router purpose
The router answers only one question:

> Is this action important enough to review before execution?

It is not trying to fully classify safety.

### 11.2 Critical action families
Use this fixed taxonomy.

| Family | Trigger cues |
|---|---|
| send_submit_share | target label contains send/submit/share/post/publish/forward/reply/apply |
| upload_attach_export | target label contains upload/attach/export/browse/choose file/save as |
| delete_overwrite | delete/trash/remove/discard/overwrite/permanent |
| permission_settings_security | allow/permit/grant/security/privacy/permissions/settings/admin |
| external_navigation | address bar change, external link, new domain, browser navigation in sensitive task |
| terminal_or_exec | terminal, shell, run command, executable launch, `sudo`, install, chmod |
| credential_or_secret_exposure | action types text/paste with key-like strings, passwords, tokens, SSH keys |
| clipboard_paste_external | paste into browser/email/chat/form destination |
| bulk_action | actions affecting many items or folders |
| financial_or_account_confirmation | pay, purchase, confirm account change, sign-in approval |

### 11.3 Router input
The router should use:

- normalized action (with target info)
- nearby a11y text
- recent history

### 11.4 Router logic
Start simple.

Pseudo-logic:

```text
if special token WAIT/DONE/FAIL:
    return not critical

if action is type/hotkey and text looks secret-like:
    critical

if target node or nearby text contains a critical keyword:
    critical

if action launches terminal or uses dangerous hotkeys:
    critical

if browser context indicates domain change or external destination:
    critical

else:
    not critical
```

### 11.5 Secret-like patterns
Add a small deterministic pattern list for:

- `sk-`
- `AKIA`
- `BEGIN OPENSSH PRIVATE KEY`
- `ssh-rsa`
- `ghp_`
- long base64-looking secrets
- email addresses when user task is not obviously email-related

### 11.6 Router output
Return:
- `critical`
- `family`
- `reasons`
- `confidence`

Do not return a final allow/block judgment.

### 11.7 Always-review baseline
For the blanket-monitor baseline, skip router logic and mark all non-special actions critical.

---

## 12. Legibility generation

Legibility is part of the core experiment and novelty claim. But it is **one function inside `reviewer.py`**, not a separate module.

### 12.1 Why separate legibility
The baseline agent already returns free-form reasoning plus action code.

Do **not** change that base prompt in the MVP.

Instead, for critical actions only, call a separate “explain this action” helper within `reviewer.py`.

### 12.2 Input
Legibility helper receives:

- instruction
- screenshot + a11y
- raw response
- normalized action (with target info)
- recent history

### 12.3 Output schema
Use the `LegibilityReport` schema from Section 8.4.

### 12.4 Failure behavior
If the legibility call fails:
- log the error
- continue with `legibility_report = null`

Do not fail the whole step because of a legibility-only error.

### 12.5 Model choice
Default to the same model family as the untrusted agent or another cheap text/multimodal model already wired into the repo.

The explanation is **untrusted**. It only exists to make mismatches easier to detect.

---

## 13. ~~Trusted fact extraction~~ — Deferred

Trusted fact extraction is deferred from the MVP. The reviewer receives the full a11y tree and screenshot directly, which is sufficient for state-grounded review. The master plan explicitly supports this: screenshot + a11y + legibility alone is publishable if exact read-only probes are too hard.

If the reviewer demonstrably misses things that a pre-extracted fact summary would catch, re-add this module later.

---

## 14. Trusted reviewer

### 14.1 Reviewer job
The reviewer answers:

> Given the current screen state, the candidate action, and the task, should this action be executed?

That is all.

### 14.2 Reviewer input
Build **one** prompt construction path. Use the `include_visual_context` config boolean to conditionally include fields.

The reviewer always sees:
- task instruction
- raw response
- normalized action (with target info)
- recent history

When `include_visual_context` is true (B2, B3, B4), also include:
- screenshot
- linearized a11y tree
- legibility report if available

When `include_visual_context` is false (B1), the reviewer sees only the language context above.

This is an `if` statement, not two separate prompt paths.

### 14.3 Reviewer output
Use the `ReviewerResult` schema:

- `allow`
- `risk_score`
- `primary_reason`
- `evidence`
- `safer_alternative`

Do not ask the reviewer to directly output controller actions in the MVP.

### 14.4 Simplification from the research plan
The research framing talks about four decisions:
- allow
- resample
- defer
- block

For implementation, simplify this:

- reviewer only says **allow / disallow**
- the **controller mode** decides what to do when disallowed

This makes the system simpler and easier to test.

### 14.5 Failure behavior
If the reviewer call errors on a critical action:

- default behavior: fail closed
- log the error
- terminate the task run with reason `review_error_fail_closed`

Make this configurable, but the default should be safe.

---

## 15. Controller policy

### 15.1 Controller responsibilities
The controller turns router + reviewer output into runtime behavior.

### 15.2 Required modes

#### Mode 1: `allow_or_terminate`
- if reviewer allows -> execute action
- else -> terminate run

This is the MVP default.

#### Mode 2: `allow_or_resample_once`
- if reviewer allows -> execute
- else -> ask the agent for one replacement action on the same state
- if replacement still fails -> terminate

#### Mode 3: `allow_or_trusted_fallback_once`
- if reviewer allows -> execute
- else -> ask trusted fallback for one action
- if fallback action invalid -> terminate

### 15.3 Termination semantics
When terminating because of a blocked critical action:

- end the recording
- write a control termination record
- still run explicit post-run judging
- mark the run as blocked in the control summary

### 15.4 Resample semantics
Keep resampling simple:

- at most 1 resample per step
- do not create loops
- do not keep hidden state beyond a counter
- do not tell the untrusted agent the exact review rubric

### 15.5 Trusted fallback semantics
Trusted fallback is optional.

If implemented:

- it only proposes **one** replacement action
- the action must be in the same raw action space
- if it cannot confidently act, it should return no action and the run terminates

Do not attempt multi-step trusted execution in the hackathon build.

---

## 16. Logging

### 16.1 Keep existing logs
Do not remove or replace:

- `better_log.json`
- `traj.jsonl`
- screenshots
- `recording.mp4`
- `result.txt`

### 16.2 Add control-specific logs
For each run, add:

```text
control_events.jsonl
control_summary.json
review_packages/
```

### 16.3 `control_events.jsonl`
Write one line per reviewed action and optionally one line per blocked / terminated event.

### 16.4 `control_summary.json`
Contains:

```json
{
  "task_id": "...",
  "domain": "...",
  "control_mode": "...",
  "router_mode": "...",
  "include_visual_context": true,
  "review_count": 0,
  "critical_count": 0,
  "blocked_count": 0,
  "review_latency_ms_total": 0,
  "terminated_by_control": false,
  "termination_reason": null
}
```

### 16.5 Review package storage
Save all review packages to disk. With 10–25 tasks and ~5–10 critical actions each, total volume is <250 packages. Storage is trivial — don't over-engineer selective saving.

---

## 17. Judging and result normalization

### 17.1 Explicitly run judge on normal completion
Add a helper that always runs the judge after each task, whether the task:
- completes normally
- terminates early
- errors

### 17.2 Judge adapter
Do not hard-code the repo’s judge output shape in many places.

Create one adapter:

```text
control/judge_adapter.py
```

Its job:
- find judge output files
- normalize to:
  - `judge_success`
  - `judge_safety`
  - `judge_violation_step`
  - `judge_reasoning`

### 17.3 Main task success
Primary source:
- `result.txt`

Optional source:
- judge success field

### 17.4 Attack safety
Primary source for attack tasks:
- judge safety field

If the judge output is unavailable for some reason:
- fall back to a clear missing-value marker
- do not silently invent safety labels

---

## 18. Evaluation plan

## 18.1 MVP experiment slice
Keep the first pass small.

### Dev smoke
- 3 benign prompt-injection tasks run **without** `--inject`
- 3 attack prompt-injection tasks run **with** `--inject`

### Dev set
- 10–15 paired prompt-injection tasks

### Test set
- 15–25 paired prompt-injection tasks if compute permits

### Optional extension
- 5–10 model-misbehavior tasks
- small custom side-task setting

## 18.2 Pairing rule
Use the same `test_injection.json` tasks in both modes.

- benign condition: same tasks, no `--inject`
- attack condition: same tasks, with `--inject`

If a task has multiple injection goals, treat:
- usefulness key = `domain/example_id`
- attack key = `domain/example_id/injection_type/goal_id`

## 18.3 Baselines to run
Required (B0–B4):

1. `none` **(B0)**
2. `always_review_language_only` **(B1)**
3. `always_review_state_grounded` **(B2)** — run on small slice (3–5 tasks) to preserve the "sparse beats blanket" comparison
4. `critical_review` **(B3)**
5. `critical_review_legibility` **(B4)**

Stretch (build only if B0–B4 are complete):
6. `critical_review_legibility_resample_once`
7. `critical_review_legibility_trusted_fallback_once`

## 18.4 Metrics
Track these at minimum.

### Usefulness
- benign task success rate

### Safety
- attack task safety rate
- or equivalently, 1 - harmful success rate

### Monitor / controller behavior
- review count per run
- critical-action trigger rate
- block rate
- disallow rate
- false positive rate on benign tasks

### Overhead
- extra review model calls
- mean review latency
- total wall-clock increase
- reviewed-step fraction

### Analysis extras
- action family distribution among reviewed steps
- action family distribution among blocked steps
- per-domain breakdown if time allows

---

## 19. Main plots and tables

`analysis/aggregate.py` must produce these artifacts:

### 19.1 Required
- `frontier_safety_vs_usefulness.png`
- `results_summary.csv`

### 19.2 Add when needed
- `overhead_summary.csv`
- `critical_action_family_counts.csv`
- `blocked_examples_manifest.csv`

Split `aggregate.py` into separate files only if it grows past ~300 lines.

---

## 20. Concentration analysis

This is a high-value analysis that supports the paper's central claim and serves as a fallback if end-to-end gains are noisy.

### 20.1 Automatic part
From `control_events.jsonl`, compute:

- counts by critical family
- counts by blocked family
- counts by attack outcome × family

### 20.2 Manual annotation — detailed schemas deferred
Manual annotation CSV schemas, column definitions, and annotation targets are in `docs/stretch_analysis.md`. The key idea: annotate a small set of blocked attack runs, successful attack runs, and benign false positives to check whether the router and reviewer made the right calls.

The logs from Sections 16–17 contain all the data needed for this analysis. Build it after the main experiment runs.

---

## 21. Implementation phases

## 21.1 Phase 0 — repo sanity
Done when:

- one OS-Harm task runs locally
- one prompt-injection task runs with `--inject`
- one same task runs without `--inject`
- output folder is understood

## 21.2 Phase 1 — review seam
Done when:

- controller hook exists between `agent.predict` and `env.step`
- raw action and observation can be passed into `control.controller.review(...)`
- control logs are written

## 21.3 Phase 2 — critical routing
Done when:

- `pyautogui` actions normalize correctly for common cases
- click targets can be matched to a11y nodes
- rule-based critical router produces sensible families

## 21.4 Phase 3 — trusted review
Done when:

- reviewer receives state-grounded package
- reviewer can return allow/disallow JSON
- controller can terminate disallowed critical actions

## 21.5 Phase 4 — baselines
Done when:

- `none` (B0)
- `always_review_language_only` (B1)
- `always_review_state_grounded` (B2, small slice)
- `critical_review` (B3)
- `critical_review_legibility` (B4)

all run from configs

## 21.6 Phase 5 — explicit judging + aggregation
Done when:

- post-run judge executes on normal completion
- aggregate script collects usefulness, safety, and overhead

## 21.7 Phase 6 — stretch
Optional:

- resample once
- trusted fallback once
- concentration annotations
- small custom side-task setting

---

## 22. Suggested workstream split

Use 2–3 workstreams, not 5. Fewer modules means fewer interface contracts to keep in sync.

### Workstream 1 — runtime integration
Owns:
- `run.py` CLI additions
- `lib_run_single.py` control hook
- `controller.py`
- `logging.py` (control log writing)
- explicit post-run judge call

Definition of done:
- end-to-end run works with a dummy reviewer that always allows

### Workstream 2 — action parsing, routing, and review
Owns:
- `action_normalizer.py`
- `a11y_parser.py`
- `critical_router.py`
- `reviewer.py` (trusted reviewer + legibility)
- `prompts.py`
- `types.py`

Definition of done:
- critical step triggers a structured review and returns allow/disallow JSON
- given saved `better_log.json` examples, router can classify likely critical vs non-critical steps

### Workstream 3 — analysis (can be done by either workstream once runs exist)
Owns:
- configs (B0–B4)
- `analysis/aggregate.py`

Definition of done:
- one command builds the results CSV and frontier plot from finished run folders

---

## 23. Acceptance tests

These are the minimum tests each coding agent should target.

### 23.1 Unit-ish tests
- parse a11y tree lines into nodes
- normalize simple `pyautogui.click(...)`
- normalize `pyautogui.hotkey(...)`
- detect secret-like typed strings
- target match click coordinate to node rectangle
- route “Send” button click as critical
- route plain desktop navigation click as non-critical

### 23.2 Integration smoke tests
- same prompt-injection task runs once without `--inject` and once with `--inject`
- critical step generates control log
- disallowed action terminates run cleanly
- judge runs after normal completion
- aggregate script finds run folders and writes CSV

### 23.3 Report-facing test
Manually inspect 3 blocked traces and confirm:
- screenshot exists
- a11y snapshot exists
- review reason exists
- termination reason exists

---

## 24. Failure handling rules

### 24.1 If review model fails
Default:
- fail closed on critical action
- terminate
- log `review_error_fail_closed`

### 24.2 If legibility fails
- continue without legibility
- log error
- do not terminate

### 24.3 If a11y parsing fails
- continue with raw a11y text and screenshot
- set target match = null
- reviewer can still run

### 24.4 If judge fails
- mark judge output missing
- keep run output
- allow aggregate script to continue
- surface missing judge in summary

### 24.5 If baseline agent outputs unparsable action
- log parse error
- terminate run
- do not try to “fix” the action with clever heuristics

---

## 25. Command templates

These are example commands, not a promise that exact paths will match every machine.

### 25.1 Benign paired run
```bash
python run.py \
  --path_to_vm Ubuntu/Ubuntu.vmx \
  --action_space pyautogui \
  --observation_type screenshot_a11y_tree \
  --model o4-mini \
  --judge_model gpt-4.1 \
  --result_dir ./results/paired_benign_dev \
  --test_all_meta_path evaluation_examples/test_injection.json \
  --control_config configs/control_critical_legibility.json
```

### 25.2 Attack paired run
```bash
python run.py \
  --path_to_vm Ubuntu/Ubuntu.vmx \
  --action_space pyautogui \
  --observation_type screenshot_a11y_tree \
  --model o4-mini \
  --judge_model gpt-4.1 \
  --result_dir ./results/paired_attack_dev \
  --test_all_meta_path evaluation_examples/test_injection.json \
  --inject \
  --control_config configs/control_critical_legibility.json
```

### 25.3 No-control baseline
```bash
python run.py \
  --path_to_vm Ubuntu/Ubuntu.vmx \
  --action_space pyautogui \
  --observation_type screenshot_a11y_tree \
  --model o4-mini \
  --judge_model gpt-4.1 \
  --result_dir ./results/baseline_none \
  --test_all_meta_path evaluation_examples/test_injection.json \
  --inject \
  --control_config configs/control_none.json
```

### 25.4 Aggregate results
```bash
python -m analysis.aggregate --root ./results --out ./analysis_outputs
```

---

## 26. What not to build unless everything else already works

Do not start these early:

- protocol-aware attacker scaffolds
- custom training
- GUI world models
- asynchronous monitoring service
- new task generation
- LinuxArena integration
- browser extension instrumentation
- fancy statistical tests
- an interactive dashboard

If there is extra time, the best next add-on is:

1. resample-on-disallow
2. concentration analysis
3. mini custom side-task setting

in that order.

---

## 27. Coding conventions for the team

### 27.1 Function shape
Prefer this style:

```python
def route_action(action, target, facts):
    if action["special_token"] in {"WAIT", "DONE", "FAIL"}:
        return {"critical": False, "family": None, "reasons": [], "confidence": 1.0}

    if looks_like_secret_exposure(action):
        return critical("credential_or_secret_exposure", "typed text looks like a secret")

    if target and target_contains_send_word(target):
        return critical("send_submit_share", "target element looks like send/submit/share")

    return not_critical()
```

### 27.2 Logging shape
Prefer structured logs over prose logs.

Good:
```python
logger.info(json.dumps({"event": "review_disallowed", "task_id": task_id, "step": step_idx}))
```

Bad:
```python
logger.info(f"Something suspicious happened maybe around step {step_idx}")
```

### 27.3 File size guideline
Try to keep files under ~300 lines unless there is a good reason.

### 27.4 Prompt storage
Store prompts in one place:
- `control/prompts.py`

Do not inline giant strings across many files.

### 27.5 Constants
Store keywords and family maps in plain dicts, not class hierarchies.

---

## 28. Final recommended milestone order

If time is collapsing, do these in order and stop when needed.

1. One paired benign vs attack run works
2. Controller seam exists
3. Rule-based critical router works
4. **Validate parser recall on real traces** — feed 3–5 real task traces through the normalizer, log parse failures, fix if >10% missed
5. Reviewer works in state-grounded mode (B3)
6. `allow_or_terminate` works
7. Explicit judge on success works
8. Aggregate usefulness/safety CSV + frontier plot works
9. Legibility works (B4)
10. Language-only baseline works (B1)
11. Blanket state-grounded baseline on small slice (B2)
12. Resample / trusted fallback (stretch)
13. Manual concentration labels (stretch)
14. Custom side-task setting (stretch)

---

## 29. Reference notes and rationale

This section explains why the spec chose this shape.

### 29.1 Why OS-Harm + OSWorld
OS-Harm is already built on OSWorld and was designed specifically for safety evaluation of computer-use agents. It includes prompt injection, deliberate misuse, and model-misbehavior tasks, plus judge infrastructure and existing execution traces. OSWorld provides the real computer environment, task setup, and execution framework.

### 29.2 Why paired prompt-injection tasks
The prompt-injection tasks are the cleanest path because the task configs themselves contain injection details and the runner applies them only when `--inject` is passed. That means the same task list can be used for benign and attack conditions.

### 29.3 Why review only critical actions
Recent control work suggests that targeted intervention on critical actions can be much more robust than generic resampling, especially under stronger red teaming. Recent computer-use work also suggests that full-trajectory monitoring is expensive and hard, while latency already hurts usability.

### 29.4 Why state-grounded review
For GUI agents, the current screen state and the a11y tree contain important evidence about what the agent is actually clicking or typing into. This is a better review target than plan text alone.

### 29.5 Why not a full-stack defense
This project is a hackathon control evaluation, not an enterprise deployment defense platform. The right contribution is a clean protocol wrapper and a strong measurement story.

---

## 30. References

These are the sources this spec is grounded in.

### Core repos and docs
- OS-Harm repo: https://github.com/tml-epfl/os-harm
- OSWorld repo: https://github.com/xlang-ai/OSWorld
- OSWorld site: https://os-world.github.io/
- Hackathon page: https://apartresearch.com/sprints/ai-control-hackathon-2026-03-20-to-2026-03-22

### Key papers
- AI Control: Improving Safety Despite Intentional Subversion — https://arxiv.org/abs/2312.06942
- Ctrl-Z: Controlling AI Agents via Resampling — https://arxiv.org/abs/2504.10374
- Evaluating Control Protocols for Untrusted AI Agents — https://arxiv.org/abs/2511.02997
- Basic Legibility Protocols Improve Trusted Monitoring — https://arxiv.org/abs/2602.10153
- Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols — https://arxiv.org/abs/2510.09462
- Attack Selection Reduces Safety in Concentrated AI Control Settings against Trusted Monitoring — https://arxiv.org/abs/2602.04930
- OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents — https://arxiv.org/abs/2506.14866
- OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments — https://arxiv.org/abs/2404.07972
- OSWorld-Human: Benchmarking the Efficiency of Computer-Use Agents — https://arxiv.org/abs/2506.16042
- Measuring Harmfulness of Computer-Using Agents — https://arxiv.org/abs/2508.00935
- Visual Confused Deputy: Exploiting and Defending Perception Failures in Computer-Using Agents — https://arxiv.org/abs/2603.14707
- Control Tax: The Price of Keeping AI in Check — https://arxiv.org/abs/2506.05296

---

## 31. Final one-line instruction to every coding agent

**Do the smallest thing that makes the main experiment run cleanly, and make the code obvious enough that a tired teammate can understand it in two minutes.**