"""Plotting and per-family output for control experiment analysis."""

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASELINE_LABELS = {
    "B0_none": "B0",
    "B1_always_language": "B1",
    "B2_always_visual": "B2",
    "B3_critical": "B3",
    "B4_critical_legibility": "B4",
}

BASELINE_COLORS = {
    "B0_none": "#888888",
    "B1_always_language": "#e07b39",
    "B2_always_visual": "#d4a017",
    "B3_critical": "#2e86c1",
    "B4_critical_legibility": "#1a9850",
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
