## What this project is

A control protocol wrapper for computer-use agents, built on top of the `os-harm` codebase. We intercept agent actions before execution, decide if they're critical, and optionally route them to a trusted reviewer. The deliverable is a thin protocol layer + evaluation — not a new agent, benchmark, or product.

## Why it matters

Harmful computer-use behavior bottlenecks through a small set of high-impact GUI actions. Reviewing only those actions using live screen state gives a better safety/usefulness tradeoff than broad monitoring.

## How the code is structured

The protocol layer lives in `control/`. Analysis scripts live in `analysis/`. Configs live in `configs/`. We patch only `run.py` and `lib_run_single.py` — everything else in the existing repo stays untouched. The insertion point is after `agent.predict(...)` and before `env.step(...)`.

Do NOT modify: `mm_agents/agent.py`, `desktop_env/*`, OSWorld internals, or judge internals.

Exception: `desktop_env/providers/vmware/provider.py` has a bug fix on our branch (IP validation in `get_ip_address()`). Do not revert it.

## How to work on this project

- Use `uv` for dependencies (`uv add`, `uv run python`). Never `pip install`.
- Python 3.12 required (`uv sync --python 3.12`). Python 3.14 breaks torch.
- VMware path: `export PATH="/Applications/VMware Fusion.app/Contents/Library:$PATH"` before any vmrun or run.py command.
- API keys: `source /Users/ashtonchew/Desktop/look-before-you-click/.env && export OPENAI_API_KEY` before any run command.
- Always pass `--observation_type screenshot_a11y_tree` and `--action_space pyautogui` explicitly.
- VM path: `--path_to_vm vmware_vm_data/Ubuntu0/Ubuntu0.vmx`. The `init_state` snapshot exists.
- Environment runs on VMware locally. Do not switch providers.
- Commit after each completed module or integration step.
- Write status to `notes/<tag>_progress.md` after major steps.

## What not to build

No new benchmarks, training pipelines, OCR, async services, databases, dashboards, browser extensions, or clever abstractions. If it's not directly needed for the current experiment, don't build it.

## Reference docs

Read these before starting work on a relevant area. Do not read all of them upfront — only the ones applicable to your current task.

### Handoff docs (primary — use these for implementation)

| File | When to read |
|---|---|
| `docs/handoff_shared.md` | **Always read first** — shared context, type schemas, integration contracts, failure rules |
| `docs/handoff_runtime.md` | Implementing WS1: run.py/lib_run_single.py patches, controller.py, logging.py, judge_adapter.py, config.py |
| `docs/handoff_parsing_routing_review.md` | Implementing WS2: types.py, action_normalizer.py, a11y_parser.py, critical_router.py, reviewer.py, prompts.py |
| `docs/handoff_analysis.md` | Implementing WS3: configs/*.json, analysis/aggregate.py |

### Other docs

| File | When to read |
|---|---|
| `docs/technical_spec.md` | Full technical specification — authoritative engineering reference. Handoff docs are extracted from this; read the original only if handoff docs lack detail on a specific section |
| `docs/critical_action_taxonomy.md` | Quick reference for router taxonomy (also in handoff_parsing_routing_review.md) |
| `docs/prompts_guide.md` | Writing or editing LLM prompts |
| `docs/milestones.md` | Deciding what to work on next |
| `docs/commands.md` | Running experiments or aggregating results |
| `docs/testing.md` | Writing tests or verifying your work |
| `docs/master_plan.md` | Writing the paper, framing novelty, or understanding overall research motivation — this file is large |
| `docs/concise_master_plan.md` | Writing the paper, framing novelty, or understanding overall research motivation — concise summary version |


## One rule

Do the smallest thing that makes the main experiment run cleanly, and make the code obvious enough that a tired teammate can understand it in two minutes.

---
name: nia
description: Use Nia MCP server for external documentation, GitHub repos, package source code, and research. Invoke when needing to index/search remote codebases, fetch library docs, explore packages, or do web research.
---

# How to use Nia

Nia provides tools for indexing and searching external repositories, research papers, local folders, documentation, packages, and performing AI-powered research. Its primary goal is to reduce hallucinations in LLMs and provide up-to-date context for AI agents.

## CRITICAL: Nia-First Workflow

**BEFORE using WebFetch or WebSearch, you MUST:**

1. **Check indexed sources first**: `manage_resource(action='list', query='relevant-keyword')` - Many sources may already be indexed
2. **If source exists**: Use `search`, `nia_grep`, `nia_read`, `nia_explore` for targeted queries
3. **If source doesn't exist but you know the URL**: Index it with `index` tool, then search
4. **Only if source unknown**: Use `nia_research(mode='quick')` to discover URLs, then index
5. **Subscribe to a source**: Use Nia to subscribe to a source by using manage_resource tool (subscribe option)

**Why this matters**: Indexed sources provide more accurate, complete context than web fetches. WebFetch returns truncated/summarized content while Nia provides full source code and documentation.

## Deterministic Workflow

1. Check if the source is already indexed using manage_resource (when listing sources, use targeted query to save tokens since users can have multiple sources indexed) or check any nia.md files for already indexed sources.
2. If it is indexed, check the tree of the source or ls relevant directories.
3. After getting the grasp of the structure (tree), use 'search', 'nia_grep', 'nia_read' for targeted searches.
4. If helpful, use the context tool to save your research findings to make them reusable for future conversations.
5. Save your findings in an .md file to track: source indexed, used, its ID, and link so you won't have to list sources in the future and can get straight to work.

## Notes

- **IMPORTANT**: Always prefer Nia tools over WebFetch/WebSearch. Nia provides full, structured content while web tools give truncated summaries.
- If the source isn't indexed, index it. Note that for docs you should always index the root link like docs.stripe.com so it will always scrape all pages.
- If you need to index something but don't know the link for that source, use nia_research (quick or deep modes).
- Once you use the index tool, do not expect it to finish in 1-3 seconds. Stop your work or do something that will make your work pause for 1-5 minutes until the source is indexed, then run manage_resource again to check its status. You can also prompt the user to wait if needed.

## Pre-WebFetch Checklist

Before ANY WebFetch or WebSearch call, verify:
- [ ] Ran `manage_resource(action='list', query='...')` for relevant keywords
- [ ] Checked nia-sources.md or nia.md files for previously indexed sources
- [ ] Confirmed no indexed source covers this information
- [ ] For GitHub/npm/PyPI URLs: These should ALWAYS be indexed, not fetched