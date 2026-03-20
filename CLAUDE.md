## What this project is

A control protocol wrapper for computer-use agents, built on top of the `os-harm` codebase. We intercept agent actions before execution, decide if they're critical, and optionally route them to a trusted reviewer. The deliverable is a thin protocol layer + evaluation — not a new agent, benchmark, or product.

## Why it matters

Harmful computer-use behavior bottlenecks through a small set of high-impact GUI actions. Reviewing only those actions using live screen state gives a better safety/usefulness tradeoff than broad monitoring.

## How the code is structured

The protocol layer lives in `control/`. Analysis scripts live in `analysis/`. Configs live in `configs/`. We patch only `run.py` and `lib_run_single.py` — everything else in the existing repo stays untouched. The insertion point is after `agent.predict(...)` and before `env.step(...)`.

Do NOT modify: `mm_agents/agent.py`, `desktop_env/*`, OSWorld internals, or judge internals.

## How to work on this project

- Use `uv` for dependencies (`uv add`, `uv run python`). Never `pip install`.
- Always pass `--observation_type screenshot_a11y_tree` and `--action_space pyautogui` explicitly.
- Environment runs on VMware locally. Do not switch providers.
- Commit after each completed module or integration step.
- Write status to `notes/<tag>_progress.md` after major steps.

## What not to build

No new benchmarks, training pipelines, OCR, async services, databases, dashboards, browser extensions, or clever abstractions. If it's not directly needed for the current experiment, don't build it.

## Reference docs

Read these before starting work on a relevant area. Do not read all of them upfront — only the ones applicable to your current task.

| File | When to read |
|---|---|
| `docs/architecture.md` | Starting any implementation work |
| `docs/data_types.md` | Building or consuming any control data structures |
| `docs/critical_action_taxonomy.md` | Working on the router or reviewer |
| `docs/prompts_guide.md` | Writing or editing LLM prompts |
| `docs/failure_handling.md` | Implementing error paths or reviewer fallbacks |
| `docs/controller_modes.md` | Implementing controller policy logic |
| `docs/workstreams.md` | Understanding which agent owns which module |
| `docs/testing.md` | Writing tests or verifying your work |
| `docs/commands.md` | Running experiments or aggregating results |
| `docs/milestones.md` | Deciding what to work on next |
| `docs/technical_spec.md` | Full technical specification — the authoritative engineering reference |
| `docs/master_plan.md` | Writing the paper, framing novelty, or understanding overall research motivation - this file is large |
| `docs/concise_master_plan.md` | Writing the paper, framing novelty, or understanding overall research motivation - this is a concise summary version|

## One rule

Do the smallest thing that makes the main experiment run cleanly, and make the code obvious enough that a tired teammate can understand it in two minutes.