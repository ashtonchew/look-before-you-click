"""Plotting and per-family output for control experiment analysis."""

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASELINE_LABELS = {
    "B0": "B0",
    "B1": "B1",
    "B2": "B2",
    "B3": "B3",
    "B4": "B4",
    "B4R": "B4R",
    "B4T": "B4T",
}

BASELINE_COLORS = {
    "B0": "#888888",
    "B1": "#e07b39",
    "B2": "#d4a017",
    "B3": "#2e86c1",
    "B4": "#1a9850",
    "B4R": "#6a3d9a",
    "B4T": "#e31a1c",
}


def write_frontier_plot(baseline_metrics: dict[str, dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "frontier_safety_vs_usefulness.png")

    fig, ax = plt.subplots(figsize=(7, 6))
    for baseline, m in sorted(baseline_metrics.items()):
        x = m["usefulness"]
        y = m["safety"]
        if x is None or y is None:
            continue
        label = BASELINE_LABELS.get(baseline, baseline)
        color = BASELINE_COLORS.get(baseline, "#333333")
        ax.scatter(x, y, s=120, c=color, zorder=3)
        ax.annotate(
            label, (x, y), textcoords="offset points", xytext=(8, 8),
            fontsize=11, fontweight="bold", color=color,
        )

    ax.set_xlabel("Usefulness (benign success rate)", fontsize=12)
    ax.set_ylabel("Safety (attack safety rate)", fontsize=12)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Safety vs Usefulness Frontier")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


_VARIANT_BASELINES = ["B4", "B4R", "B4T"]


def write_variant_comparison_plot(
    baseline_metrics: dict[str, dict], out_dir: str,
) -> str | None:
    """Write a grouped bar chart comparing B4 vs B4R vs B4T.

    Returns None if fewer than 2 of the three variants are present.
    """
    present = [b for b in _VARIANT_BASELINES if b in baseline_metrics]
    if len(present) < 2:
        return None

    path = os.path.join(out_dir, "variant_comparison_B4_B4R_B4T.png")

    metric_keys = ["usefulness", "safety", "false_positive_rate"]
    metric_labels = ["Usefulness", "Safety", "FP Rate"]

    fig, axes = plt.subplots(1, len(metric_keys), figsize=(4 * len(metric_keys), 5))
    if len(metric_keys) == 1:
        axes = [axes]

    bar_width = 0.6 / len(present)

    for ax_idx, (key, label) in enumerate(zip(metric_keys, metric_labels)):
        ax = axes[ax_idx]
        for i, baseline in enumerate(present):
            val = baseline_metrics[baseline].get(key)
            if val is None:
                val = 0.0
            color = BASELINE_COLORS.get(baseline, "#333333")
            offset = (i - len(present) / 2 + 0.5) * bar_width
            ax.bar(offset, val, bar_width * 0.9, color=color,
                   label=baseline if ax_idx == 0 else "")
        ax.set_title(label, fontsize=11)
        ax.set_ylim(0, 1.05)
        ax.set_xticks([])
        ax.grid(axis="y", alpha=0.3)

    handles = [plt.Rectangle((0, 0), 1, 1, color=BASELINE_COLORS.get(b, "#333333"))
               for b in present]
    fig.legend(handles, present, loc="lower center", ncol=len(present), fontsize=10)
    fig.suptitle("Protocol Variant Comparison", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0.08, 1, 0.95])
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def write_family_counts_csv(runs: list[dict], read_control_events, out_dir: str) -> str | None:
    """Write critical action family distribution from control_events.jsonl.

    read_control_events is passed in to avoid circular imports.
    """
    counts = defaultdict(lambda: {"reviewed": 0, "blocked": 0})
    has_data = False

    for r in runs:
        events = read_control_events(r["run_dir"])
        for event in events:
            router = event.get("router_decision", {})
            family = router.get("family")
            if family:
                has_data = True
                counts[family]["reviewed"] += 1
                controller = event.get("controller_decision", {})
                if not controller.get("execute", True):
                    counts[family]["blocked"] += 1

    if not has_data:
        return None

    path = os.path.join(out_dir, "critical_action_family_counts.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["family", "reviewed_count", "blocked_count"])
        for family, c in sorted(counts.items(), key=lambda x: -x[1]["reviewed"]):
            writer.writerow([family, c["reviewed"], c["blocked"]])
    return path
