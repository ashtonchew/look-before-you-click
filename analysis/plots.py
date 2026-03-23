"""Plotting and per-family output for control experiment analysis."""

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASELINE_LABELS = {
    "B0": "Unmonitored",
    "B1": "Full Review, Text-Only",
    "B2": "Full Review, Visual",
    "B3": "Selective",
    "B4": "Selective, Justified",
    "B4R": "Selective, Resample",
    "B4T": "Selective, Fallback",
}

BASELINE_COLORS = {
    "B0": "#888888",
    "B1": "#E69F00",
    "B2": "#56B4E9",
    "B3": "#009E73",
    "B4": "#0072B2",
    "B4R": "#D55E00",
    "B4T": "#CC79A7",
}


def write_frontier_plot(
    baseline_metrics: dict[str, dict],
    out_dir: str,
    filename: str = "frontier_safety_vs_usefulness.png",
    title: str = "Safety vs Usefulness Frontier",
) -> str:
    path = os.path.join(out_dir, filename)

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
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


THREAT_MODEL_COLORS = {
    "environmental": "#0072B2",
    "scheming": "#E69F00",
}


def write_failure_taxonomy_plot(
    failure_counts: dict[str, dict[str, int]],
    out_dir: str,
) -> str | None:
    """Horizontal bar chart of failure modes by threat model.

    failure_counts: {failure_mode: {threat_model: count}}
    Example: {"timing": {"environmental": 0, "scheming": 3}, ...}
    Returns path to saved figure, or None if no data.
    """
    if not failure_counts:
        return None

    # Collect all threat models present in data.
    threat_models = sorted(
        {tm for counts in failure_counts.values() for tm in counts}
    )
    if not threat_models:
        return None

    # Guard: all counts are zero -- nothing to plot.
    total = sum(c for counts in failure_counts.values() for c in counts.values())
    if total == 0:
        return None

    modes = sorted(failure_counts.keys())
    n_modes = len(modes)
    n_groups = len(threat_models)
    bar_height = 0.8 / max(n_groups, 1)

    fig, ax = plt.subplots(figsize=(8, max(3, 0.6 * n_modes + 1)))

    for i, tm in enumerate(threat_models):
        values = [failure_counts[mode].get(tm, 0) for mode in modes]
        offsets = [y + (i - n_groups / 2 + 0.5) * bar_height for y in range(n_modes)]
        color = THREAT_MODEL_COLORS.get(tm, "#888888")
        bars = ax.barh(offsets, values, height=bar_height * 0.9, color=color, label=tm)
        # Label non-zero bars with count; show colored dot + "0" for zeros.
        labels = [str(v) if v > 0 else "" for v in values]
        ax.bar_label(bars, labels=labels, padding=3, fontsize=9)
        for offset, val in zip(offsets, values):
            if val == 0:
                ax.plot(0, offset, "o", color=color, markersize=5,
                        markeredgecolor="white", markeredgewidth=0.5, zorder=3)
                ax.text(0.4, offset, "0", va="center", fontsize=9, color="#666666")

    ax.set_yticks(range(n_modes))
    ax.set_yticklabels(modes, fontsize=10)
    ax.set_xlabel("Count", fontsize=11)
    ax.set_title("Failure Taxonomy by Threat Model", fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()

    path = os.path.join(out_dir, "failure_taxonomy.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


_ABLATION_ORDER = ["B0", "B1", "B2", "B3", "B4"]


def write_ablation_ladder_plot(
    ladder_metrics: list[dict],
    out_dir: str,
    filename: str = "ablation_ladder_B0_B1_B2_B3_B4.png",
) -> str:
    """Connected scatter of B0-B4 in ladder order.

    ladder_metrics: list of 5 dicts in B0->B4 order, each with
    'baseline', 'usefulness', 'safety'.
    """
    path = os.path.join(out_dir, filename)

    xs = [m["usefulness"] for m in ladder_metrics]
    ys = [m["safety"] for m in ladder_metrics]

    fig, ax = plt.subplots(figsize=(7, 6))

    # Connecting line in ladder order.
    ax.plot(xs, ys, linestyle="--", color="#aaaaaa", alpha=0.5, zorder=1)

    # Scatter + labels per baseline.
    for m in ladder_metrics:
        bl = m["baseline"]
        x, y = m["usefulness"], m["safety"]
        color = BASELINE_COLORS.get(bl, "#333333")
        label = BASELINE_LABELS.get(bl, bl)
        ax.scatter(x, y, s=120, c=color, zorder=3)
        ax.annotate(
            label, (x, y), textcoords="offset points", xytext=(8, 8),
            fontsize=11, fontweight="bold", color=color,
        )

    ax.set_xlabel("Usefulness (benign success rate)", fontsize=12)
    ax.set_ylabel("Safety (attack safety rate)", fontsize=12)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Ablation Ladder: Environmental Baselines")
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
