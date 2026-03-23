"""Merge corrected (B0/B4) and expansion (B1/B2/B3) environmental metrics
into a single ablation-ladder CSV and figure.

Usage:
    uv run python -m analysis.ablation_ladder \
        --corrected analysis_outputs/final_corrected \
        --expansion analysis_outputs/expansion \
        --out analysis_outputs/ablation_ladder
"""

import argparse
import csv
import os

from analysis.plots import write_ablation_ladder_plot, write_frontier_plot

LADDER_ORDER = ["B0", "B1", "B2", "B3", "B4"]
CORRECTED_BASELINES = {"B0", "B4"}
EXPANSION_BASELINES = {"B1", "B2", "B3"}


def _read_env_rows(csv_path: str) -> list[dict]:
    """Read results_summary.csv and return only environmental rows."""
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Missing input: {csv_path}")
    rows = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("threat_model") == "environmental":
                rows.append(row)
    return rows


def _compute_metrics(rows: list[dict], baseline: str) -> dict:
    """Compute usefulness, safety, and cost for one baseline from per-run rows."""
    benign = [r for r in rows if r["baseline"] == baseline and r["is_attack"] == "False"]
    attack = [r for r in rows if r["baseline"] == baseline and r["is_attack"] == "True"]

    benign_success = [r for r in benign if r["main_task_success"] == "True"]
    usefulness = len(benign_success) / len(benign) if benign else None

    attack_safe = [r for r in attack if r["safety"] == "True"]
    safety = len(attack_safe) / len(attack) if attack else None

    all_runs = [r for r in rows if r["baseline"] == baseline]
    cost_values = [float(r.get("estimated_cost_usd", 0)) for r in all_runs]
    mean_cost = sum(cost_values) / len(cost_values) if cost_values else None

    return {
        "baseline": baseline,
        "usefulness": usefulness,
        "safety": safety,
        "n_benign": len(benign),
        "n_attack": len(attack),
        "mean_cost_per_task_usd": mean_cost,
    }


def merge_ladder_metrics(
    corrected_csv: str,
    expansion_csv: str,
) -> list[dict]:
    """Return 5 metric dicts in B0-B4 ladder order.

    B0, B4 come from corrected_csv. B1, B2, B3 come from expansion_csv.
    Raises ValueError if any baseline is missing environmental data.
    """
    corrected_rows = _read_env_rows(corrected_csv)
    expansion_rows = _read_env_rows(expansion_csv)

    metrics = []
    for bl in LADDER_ORDER:
        if bl in CORRECTED_BASELINES:
            m = _compute_metrics(corrected_rows, bl)
            m["source_cohort"] = "final_corrected"
            m["source_file"] = corrected_csv
        else:
            m = _compute_metrics(expansion_rows, bl)
            m["source_cohort"] = "expansion"
            m["source_file"] = expansion_csv

        if m["usefulness"] is None and m["n_benign"] == 0:
            raise ValueError(
                f"Baseline {bl}: no environmental benign rows found in "
                f"{m['source_file']}"
            )
        if m["safety"] is None and m["n_attack"] == 0:
            raise ValueError(
                f"Baseline {bl}: no environmental attack rows found in "
                f"{m['source_file']}"
            )
        metrics.append(m)

    return metrics


def write_metrics_csv(metrics: list[dict], out_dir: str) -> str:
    """Write ablation_ladder_metrics.csv."""
    path = os.path.join(out_dir, "ablation_ladder_metrics.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "baseline", "usefulness", "safety",
            "n_benign", "n_attack", "mean_cost_per_task_usd",
            "source_cohort", "source_file",
        ])
        for m in metrics:
            cost = m.get("mean_cost_per_task_usd")
            writer.writerow([
                m["baseline"],
                f"{m['usefulness']:.4f}" if m["usefulness"] is not None else "",
                f"{m['safety']:.4f}" if m["safety"] is not None else "",
                m["n_benign"],
                m["n_attack"],
                f"{cost:.6f}" if cost is not None else "",
                m["source_cohort"],
                m["source_file"],
            ])
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate combined ablation ladder figure (B0-B4, environmental only)."
    )
    parser.add_argument(
        "--corrected", required=True,
        help="Path to final_corrected aggregate output dir (contains results_summary.csv)",
    )
    parser.add_argument(
        "--expansion", required=True,
        help="Path to expansion aggregate output dir (contains results_summary.csv)",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output directory for ablation ladder artifacts",
    )
    args = parser.parse_args(argv)

    corrected_csv = os.path.join(args.corrected, "results_summary.csv")
    expansion_csv = os.path.join(args.expansion, "results_summary.csv")

    metrics = merge_ladder_metrics(corrected_csv, expansion_csv)

    os.makedirs(args.out, exist_ok=True)

    csv_path = write_metrics_csv(metrics, args.out)
    print(f"CSV: {csv_path}")

    for m in metrics:
        u = f"{m['usefulness']:.3f}" if m['usefulness'] is not None else "N/A"
        s = f"{m['safety']:.3f}" if m['safety'] is not None else "N/A"
        c = f"${m['mean_cost_per_task_usd']:.4f}" if m.get('mean_cost_per_task_usd') is not None else "N/A"
        print(f"  {m['baseline']}: usefulness={u}  safety={s}  cost/task={c}  "
              f"n_benign={m['n_benign']}  n_attack={m['n_attack']}  "
              f"source={m['source_cohort']}")

    png_path = write_ablation_ladder_plot(metrics, args.out)
    print(f"PNG: {png_path}")

    # Also emit a 5-baseline frontier plot (same data, scatter format)
    frontier_metrics = {
        m["baseline"]: {"usefulness": m["usefulness"], "safety": m["safety"]}
        for m in metrics
    }
    frontier_path = write_frontier_plot(
        frontier_metrics, args.out,
        filename="frontier_safety_vs_usefulness_5baseline.png",
        title="Safety vs Usefulness Frontier (B0-B4)",
    )
    print(f"PNG: {frontier_path}")


if __name__ == "__main__":
    main()
