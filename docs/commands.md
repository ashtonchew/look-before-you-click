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
python -m analysis.aggregate_results --root ./results --out ./analysis_outputs
python -m analysis.plot_frontier --input ./analysis_outputs/results_summary.csv
```
