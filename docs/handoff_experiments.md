# Handoff: Running Experiments

**Read [handoff_shared.md](/Users/ashtonchew/Desktop/look-before-you-click/docs/handoff_shared.md) first, then [handoff_analysis.md](/Users/ashtonchew/Desktop/look-before-you-click/docs/handoff_analysis.md).**

This document is the runbook for the next experiment phase.

---

## 1. What This Phase Is Trying to Prove

### Primary comparison
The main result is still the `B0-B4` frontier:
- whether sparse critical-action review improves safety over no control and language-only review
- whether it preserves more usefulness than blanket state-grounded review

### Secondary comparison
`B4R` and `B4T` are immediate follow-on variants:
- `B4R`: can one resample recover suspicious but salvageable actions?
- `B4T`: can one trusted fallback action improve outcomes on high-impact ambiguous steps?

These are part of the protocol story, but they do **not** replace the core `B0-B4` claim.

---

## 2. Default Dataset

Use this by default for both benign and attack:
- meta path: `evaluation_examples/test_injection_selected.json`
- config base dir: `evaluation_examples_selected`

### Why
Phase 0 showed that the full `test_injection.json` is diluted by many low-yield variants. The selected set keeps the prompt-injection evaluation paired but high-signal.

### Optional later expansion
Only after the selected-set dev matrix is stable:
- meta path: `evaluation_examples/test_injection.json`
- default config base dir

That full-set run is optional expansion, not the default dev protocol.

---

## 3. Preconditions

Before any run:
1. VMware VM exists at `os-harm/vmware_vm_data/Ubuntu0/Ubuntu0.vmx`
2. VMware Fusion is running
3. `OPENAI_API_KEY` is set
4. Python 3.12 environment is working
5. Quick import check passes

```bash
cd os-harm
PYTHONPATH=.. uv run python -c "from control.controller import review; print('ok')"
```

---

## 4. Common Command Template

All runs are launched from `os-harm/`.

```bash
COMMON_ARGS="
  --path_to_vm vmware_vm_data/Ubuntu0/Ubuntu0.vmx
  --action_space pyautogui
  --observation_type screenshot_a11y_tree
  --model o4-mini
  --judge_model gpt-4.1
  --test_all_meta_path evaluation_examples/test_injection_selected.json
  --test_config_base_dir evaluation_examples_selected
"
```

### Reviewer / legibility models
- `B0`: no reviewer flags needed
- `B1`, `B2`, `B3`: add `--reviewer_model gpt-4.1`
- `B4`, `B4R`, `B4T`: add `--reviewer_model gpt-4.1 --legibility_model o4-mini`
- `B4T`: if you want a separate fallback model, also add `--trusted_fallback_model gpt-4.1`

---

## 5. Run Order

Run phases in this order and do not skip gates:

1. Smoke
2. Core matrix: `B0-B4`
3. Secondary variants: `B4R`
4. Secondary variants: `B4T`
5. Aggregation

If a gate fails, stop and fix the issue before continuing.

---

## 6. Smoke Runs

### Purpose
Verify the pipeline end-to-end before the full matrix:
- control logs are written
- reviewer output parses
- selected paired set is wired correctly
- `B4R` exercises at least one `RESAMPLE` branch
- `B4T` exercises at least one `DEFER_TO_TRUSTED` branch

### Recommended smoke domains
Use:
- `chrome`
- `thunderbird`

These are the highest-yield domains from Phase 0.

### Smoke commands

#### `B4` benign
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --domain chrome \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/smoke_benign_B4 \
  --control_config ../configs/control_critical_legibility.json
```

#### `B4` attack
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --domain chrome \
  --inject \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/smoke_attack_B4 \
  --control_config ../configs/control_critical_legibility.json
```

#### `B4R` attack
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --domain thunderbird \
  --inject \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/smoke_attack_B4R \
  --control_config ../configs/control_critical_legibility_resample_once.json
```

#### `B4T` attack
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --domain thunderbird \
  --inject \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --trusted_fallback_model gpt-4.1 \
  --result_dir ./results/smoke_attack_B4T \
  --control_config ../configs/control_critical_legibility_trusted_fallback_once.json
```

### Smoke gate
After smoke, confirm:
- `control_events.jsonl` exists
- `control_summary.json` exists
- `review_packages/` exists for reviewed actions
- `judgment/.../judgment.json` exists
- at least one reviewed critical action exists
- at least one `RESAMPLE` decision appears in the `B4R` smoke outputs
- at least one `DEFER_TO_TRUSTED` decision appears in the `B4T` smoke outputs

If the last two do not happen, stop and debug prompts / policy before full runs.

---

## 7. Core Matrix: `B0-B4`

### Benign condition
Use the selected paired set with **no** `--inject`.

### Attack condition
Use the **same selected paired set** with `--inject`.

### `B0`
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --result_dir ./results/dev_benign_B0 \
  --control_config ../configs/control_none.json

cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --inject \
  --result_dir ./results/dev_attack_B0 \
  --control_config ../configs/control_none.json
```

### `B1`
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --reviewer_model gpt-4.1 \
  --result_dir ./results/dev_benign_B1 \
  --control_config ../configs/control_always_review_language_only.json

cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --inject \
  --reviewer_model gpt-4.1 \
  --result_dir ./results/dev_attack_B1 \
  --control_config ../configs/control_always_review_language_only.json
```

### `B2` small slice only
Run `B2` only on this declared slice:
- `chrome`
- `thunderbird`
- `vs_code`

Run those three domains sequentially into the same result directories.

```bash
cd os-harm
for DOMAIN in chrome thunderbird vs_code; do
  PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
    --domain $DOMAIN \
    --reviewer_model gpt-4.1 \
    --result_dir ./results/dev_benign_B2 \
    --control_config ../configs/control_always_review_state_grounded.json
done

cd os-harm
for DOMAIN in chrome thunderbird vs_code; do
  PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
    --domain $DOMAIN \
    --inject \
    --reviewer_model gpt-4.1 \
    --result_dir ./results/dev_attack_B2 \
    --control_config ../configs/control_always_review_state_grounded.json
done
```

### `B3`
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --reviewer_model gpt-4.1 \
  --result_dir ./results/dev_benign_B3 \
  --control_config ../configs/control_critical.json

cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --inject \
  --reviewer_model gpt-4.1 \
  --result_dir ./results/dev_attack_B3 \
  --control_config ../configs/control_critical.json
```

### `B4`
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/dev_benign_B4 \
  --control_config ../configs/control_critical_legibility.json

cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --inject \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/dev_attack_B4 \
  --control_config ../configs/control_critical_legibility.json
```

### Core-matrix gate
Before `B4R` / `B4T`, confirm:
- all `B0-B4` runs finished
- no result directories were mixed across benign / attack
- judge outputs exist for each run
- aggregation can parse the core matrix without manual patching

---

## 8. Secondary Variants

Run these only after the core matrix is stable.

### `B4R`
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/dev_benign_B4R \
  --control_config ../configs/control_critical_legibility_resample_once.json

cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --inject \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --result_dir ./results/dev_attack_B4R \
  --control_config ../configs/control_critical_legibility_resample_once.json
```

### `B4T`
```bash
cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --trusted_fallback_model gpt-4.1 \
  --result_dir ./results/dev_benign_B4T \
  --control_config ../configs/control_critical_legibility_trusted_fallback_once.json

cd os-harm
PYTHONPATH=.. uv run python run.py $COMMON_ARGS \
  --inject \
  --reviewer_model gpt-4.1 \
  --legibility_model o4-mini \
  --trusted_fallback_model gpt-4.1 \
  --result_dir ./results/dev_attack_B4T \
  --control_config ../configs/control_critical_legibility_trusted_fallback_once.json
```

### Variant gate
Confirm before analysis:
- `B4R` shows at least one actual resample attempt in logs
- `B4T` shows at least one actual trusted fallback attempt in logs
- the aggregate script picks up `B4R` and `B4T` as distinct labels

---

## 9. Aggregation

From the project root:

```bash
cd /Users/ashtonchew/Desktop/look-before-you-click
PYTHONPATH=. uv run python -m analysis.aggregate --root os-harm/results --out ./analysis_outputs
```

Expected artifacts:
- `analysis_outputs/results_summary.csv`
- `analysis_outputs/frontier_safety_vs_usefulness.png`
- `analysis_outputs/protocol_variant_summary.csv`
- `analysis_outputs/critical_action_family_counts.csv`

---

## 10. What to Look For

### Good primary signs
- `B0` attack runs show harmful successes
- `B3` and `B4` improve attack safety
- `B3` and `B4` preserve benign usefulness better than `B1` and `B2`
- reviewed-step fraction stays sparse for `B3` and `B4`

### Good secondary signs
- `B4R` rescues some suspicious-but-fixable critical actions
- `B4T` helps on high-impact ambiguous steps where blocking is too blunt
- rescue behavior improves outcomes without exploding review overhead

### Warning signs
- selected-set attack runs show no unsafe behavior at all
- `B3` / `B4` block too many benign steps
- `B4R` repeatedly fails to rescue anything useful
- `B4T` acts too aggressively or degrades usefulness

---

## 11. Claim-Safety Rules

### What `B0-B4` can support
- whether sparse critical-action review helps safety
- whether sparse review preserves more usefulness than blanket review
- whether legibility helps over `B3`

### What `B4R/B4T` can support
- whether escalation policy matters after a risky action is caught
- whether one resample or one trusted fallback improves the `B4` protocol

### What requires reruns
Rerun the affected matrix if any of these change midstream:
- reviewer decision schema
- controller-mode semantics
- default selected task set
- router family definitions
- prompt policy for allowed reviewer decisions per mode

Do not mix pre-change and post-change runs in the same headline comparison.

---

## 12. Definition of Done

- smoke passes
- `B0-B4` complete on the selected paired set
- `B2` complete on the declared small slice
- `B4R` complete
- `B4T` complete
- aggregation outputs the primary and secondary artifacts
- results are reviewed with claim discipline before any paper framing is locked
