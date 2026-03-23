# Commands

Always pass `--observation_type screenshot_a11y_tree` and `--action_space pyautogui` explicitly. The repo defaults are different from what we want.

## Benign paired run
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

## Attack paired run
Same as above but add `--inject` and change `--result_dir`.

## No-control baseline
Same as above but use `--control_config configs/control_none.json`.

## Aggregate + plot
```bash
# Run from project root, not os-harm/
# Point --root at one cohort directory, not the container:
uv run python -m analysis.aggregate --root results_backup/final_historical --out ./analysis_outputs/final_historical
uv run python -m analysis.aggregate --root results_backup/smoke --out ./analysis_outputs/smoke
```
Produces `results_summary.csv`, `frontier_safety_vs_usefulness.png`, and `critical_action_family_counts.csv`.

## Expansion runs (B1/B2/B3 + A2)
```bash
DRY_RUN=1 bash os-harm/run_final_push_expansion.sh   # verify commands
NUM_ENVS=3 bash os-harm/run_final_push_expansion.sh   # run with 3 VMs
bash os-harm/run_final_push_expansion.sh               # run with default 5 VMs
```
12 run groups. Syncs results to `results_backup/expansion/`.

## Corrective reruns (19 targeted tasks)
```bash
DRY_RUN=1 bash os-harm/run_final_push_corrections.sh  # verify commands
bash os-harm/run_final_push_corrections.sh             # run with default 5 VMs
```
9 run groups. Syncs results to `results_backup/rerun_raw/`.

## Assemble final_corrected cohort
```bash
DRY_RUN=1 bash os-harm/assemble_final_corrected.sh   # preview overlay plan
bash os-harm/assemble_final_corrected.sh              # build final_corrected/
```
Copies `final_historical/` into `final_corrected/`, then overlays 19 corrected task dirs from `rerun_raw/`. Mapping is in `configs/assembly_corrections_map.json`. Never mutates `final_historical/`.

## Ablation ladder (combined 5-baseline figure)
```bash
uv run python -m analysis.ablation_ladder \
  --corrected analysis_outputs/final_corrected \
  --expansion analysis_outputs/expansion \
  --out analysis_outputs/ablation_ladder
```
Merges B0/B4 from corrected cohort and B1/B2/B3 from expansion cohort into a single environmental ablation ladder. Produces `ablation_ladder_metrics.csv` and `ablation_ladder_B0_B1_B2_B3_B4.png`.
