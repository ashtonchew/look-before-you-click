# Architecture

```
run.py
  └── lib_run_single.run_single_example(...)
        ├── agent.predict(instruction, obs)          # UNTOUCHED
        ├── control.controller.handle_actions(...)   # OUR LAYER
        │     ├── action_normalizer       → pyautogui string to NormalizedAction
        │     ├── a11y_parser             → linearized tree to node list + target match
        │     ├── critical_router         → rule-based: is this action critical?
        │     ├── fact_extractor          → deterministic: URLs, emails, danger terms
        │     ├── legibility_client       → LLM call, critical only, untrusted output
        │     ├── trusted_reviewer        → LLM call, critical only, trusted output
        │     └── controller_policy       → allow / terminate / resample / fallback
        ├── env.step(...)                            # UNTOUCHED
        ├── OS-Harm logging                          # UNTOUCHED
        ├── control logging                          # NEW
        └── explicit post-run judge call             # NEW
```

## File layout

### Patch (minimal changes only)
- `run.py` — CLI flags, wire control config
- `lib_run_single.py` — controller hook between predict and step

### New: `control/`
- `config.py` — load JSON control config
- `types.py` — NormalizedAction, RouterDecision, ReviewPackage, etc.
- `action_normalizer.py` — pyautogui string to NormalizedAction
- `a11y_parser.py` — tree parsing + click target matching
- `critical_router.py` — rule-based router
- `fact_extractor.py` — deterministic URL/email/secret extraction
- `legibility.py` — structured explanation LLM call (critical only)
- `trusted_reviewer.py` — allow/disallow LLM call (critical only)
- `controller.py` — orchestrates router → reviewer → policy
- `prompts.py` — ALL prompt templates (single source of truth)
- `log_io.py` — write control_events.jsonl + control_summary.json
- `metrics.py` — review rate, block rate, latency
- `judge_adapter.py` — normalize judge output

### New: `analysis/`
- `aggregate_results.py` — run folders → results_summary.csv
- `export_examples.py` — blocked/reviewed trace packets
- `plot_frontier.py` — safety-vs-usefulness plot
- `summarize_overhead.py` — overhead_summary.csv

### New: `configs/`
- `control_none.json`
- `control_always_review.json`
- `control_critical_no_legibility.json`
- `control_critical_legibility.json`
- `control_critical_legibility_resample.json`
