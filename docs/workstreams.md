# Workstreams

Use this split for parallel agents. Do not duplicate work across streams.

## Agent A — Runtime Integration
**Owns:** `run.py` CLI additions, `lib_run_single.py` control hook, explicit post-run judge call, control log writing.
**Done when:** End-to-end run works with a dummy reviewer that always allows.

## Agent B — Action Parsing & Routing
**Owns:** `action_normalizer.py`, `a11y_parser.py`, `critical_router.py`, `fact_extractor.py`.
**Done when:** Given saved `better_log.json` examples, the router classifies likely critical vs non-critical steps.

## Agent C — Reviewer & Legibility
**Owns:** `legibility.py`, `trusted_reviewer.py`, `prompts.py`, controller disallow behavior.
**Done when:** Critical step triggers a structured review and returns allow/disallow JSON.

## Agent D — Analysis & Experiment Harness
**Owns:** configs, aggregate scripts, CSV outputs, plots, example trace export.
**Done when:** One command builds results table and frontier plot from finished run folders.
