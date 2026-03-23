"""Retrospective cost estimation for control protocol LLM calls.

Estimates USD cost per control event from logged data (control_events.jsonl,
control_summary.json) using known prompt sizes and model pricing.

Usage:
    uv run python -m analysis.cost_estimator \
        --root results_backup/final_corrected \
        --out analysis_outputs/cost
"""

import argparse
import csv
import json
import math
import os
import sys


# NOTE: aggregate.py imports estimate_event_cost from this module, so we
# must NOT import from aggregate at module level (circular import).
# The CLI main() performs a lazy import instead.


# USD per 1K tokens (March 2026 pricing)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.4-mini": {"input": 0.00075, "output": 0.0045},
    "gpt-4o-mini":  {"input": 0.00015, "output": 0.0006},
}

# Default screenshot dimensions (Ubuntu VM at 1920x985)
_DEFAULT_WIDTH = 1920
_DEFAULT_HEIGHT = 985

# Estimated text token counts per call type (from prompt template analysis).
# These exclude screenshot tokens which are computed separately.
_REVIEW_TEXT_TOKENS_NO_VISUAL = 1200
_REVIEW_TEXT_TOKENS_VISUAL = 2400
_REVIEW_TEXT_TOKENS_VISUAL_WITH_LEGIBILITY = 2590
_REVIEW_OUTPUT_TOKENS = 150

_LEGIBILITY_TEXT_TOKENS = 1950
_LEGIBILITY_OUTPUT_TOKENS = 190

_FALLBACK_TEXT_TOKENS_NO_VISUAL = 1200
_FALLBACK_TEXT_TOKENS_VISUAL = 2600
_FALLBACK_OUTPUT_TOKENS = 100


def screenshot_tokens(
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    model: str = "gpt-5.4-mini",
) -> int:
    """Estimate image token count for a screenshot, model-dependent.

    gpt-4o-mini uses the old tile formula (scale shortest side to 768,
    tile into 512x512 blocks).
    gpt-5.4-mini and newer use the patch formula (32x32 patches, cap at 1536).
    """
    if model in ("gpt-4o-mini", "gpt-4o"):
        # Old tile formula
        scale = 768 / min(width, height)
        sw = int(width * scale)
        sh = int(height * scale)
        tiles = math.ceil(sw / 512) * math.ceil(sh / 512)
        return 85 + 170 * tiles
    else:
        # New patch formula: 32x32 pixel patches, capped at 1536
        patches = math.ceil(width / 32) * math.ceil(height / 32)
        return min(patches, 1536)


def _token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost for a single LLM call."""
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    return (input_tokens / 1000 * pricing["input"]
            + output_tokens / 1000 * pricing["output"])


def estimate_event_cost(event: dict, summary: dict) -> dict:
    """Estimate USD cost for one control event from logged data.

    Returns dict with legibility_cost_usd, review_cost_usd,
    fallback_cost_usd, and total_cost_usd.
    """
    legibility_cost = 0.0
    review_cost = 0.0
    fallback_cost = 0.0

    visual = summary.get("include_visual_context", False)
    reviewer_model = event.get("reviewer_model", "gpt-5.4-mini")
    legibility_model = "gpt-4o-mini"

    has_legibility = event.get("legibility_report") is not None
    has_review = event.get("reviewer_result") is not None
    has_fallback = event.get("trusted_fallback_result") is not None

    # Legibility call (always includes screenshot regardless of visual config)
    if has_legibility:
        img_tokens = screenshot_tokens(model=legibility_model)
        input_tokens = _LEGIBILITY_TEXT_TOKENS + img_tokens
        legibility_cost = _token_cost(legibility_model, input_tokens,
                                      _LEGIBILITY_OUTPUT_TOKENS)

    # Review call
    if has_review:
        if visual:
            if has_legibility:
                text_tokens = _REVIEW_TEXT_TOKENS_VISUAL_WITH_LEGIBILITY
            else:
                text_tokens = _REVIEW_TEXT_TOKENS_VISUAL
            img_tokens = screenshot_tokens(model=reviewer_model)
            input_tokens = text_tokens + img_tokens
        else:
            input_tokens = _REVIEW_TEXT_TOKENS_NO_VISUAL
        review_cost = _token_cost(reviewer_model, input_tokens,
                                  _REVIEW_OUTPUT_TOKENS)

    # Trusted fallback call
    if has_fallback:
        if visual:
            img_tokens = screenshot_tokens(model=reviewer_model)
            input_tokens = _FALLBACK_TEXT_TOKENS_VISUAL + img_tokens
        else:
            input_tokens = _FALLBACK_TEXT_TOKENS_NO_VISUAL
        fallback_cost = _token_cost(reviewer_model, input_tokens,
                                    _FALLBACK_OUTPUT_TOKENS)

    return {
        "legibility_cost_usd": legibility_cost,
        "review_cost_usd": review_cost,
        "fallback_cost_usd": fallback_cost,
        "total_cost_usd": legibility_cost + review_cost + fallback_cost,
    }


def estimate_run_cost(events: list[dict], summary: dict) -> float:
    """Sum estimated cost across all control events in one run."""
    return sum(estimate_event_cost(e, summary)["total_cost_usd"]
               for e in events)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_COST_CSV_COLUMNS = [
    "baseline", "n_runs", "total_reviews", "total_cost_usd",
    "mean_cost_per_task_usd", "mean_cost_per_review_usd",
    "legibility_cost_usd", "review_cost_usd", "fallback_cost_usd",
]


def main(argv: list[str] | None = None) -> None:
    # Lazy import to avoid circular dependency with aggregate.py
    from analysis.aggregate import (
        discover_runs, read_control_events, read_control_summary, infer_baseline,
    )

    parser = argparse.ArgumentParser(
        description="Estimate control protocol cost from experiment logs."
    )
    parser.add_argument("--root", required=True, help="Root results directory")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--judge_model", default="gpt-4.1")
    parser.add_argument("--judge_type", default="aer")
    parser.add_argument("--sys_prompt_version", default="v3")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        print(f"ERROR: --root does not exist: {args.root}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)

    runs = discover_runs(args.root, args.judge_model, args.judge_type,
                         args.sys_prompt_version)
    if not runs:
        print(f"WARNING: no run folders found under {args.root}",
              file=sys.stderr)
        return

    # Aggregate by baseline
    from collections import defaultdict
    by_baseline: dict[str, dict] = defaultdict(lambda: {
        "n_runs": 0, "total_reviews": 0,
        "legibility_cost": 0.0, "review_cost": 0.0,
        "fallback_cost": 0.0, "total_cost": 0.0,
    })

    for run in runs:
        run_dir = run["run_dir"]
        summary_raw = read_control_summary(run_dir)
        baseline = infer_baseline(summary_raw, run_dir)
        summary = summary_raw or {}
        events = read_control_events(run_dir)

        bucket = by_baseline[baseline]
        bucket["n_runs"] += 1
        bucket["total_reviews"] += summary.get("review_count", 0)

        for event in events:
            costs = estimate_event_cost(event, summary)
            bucket["legibility_cost"] += costs["legibility_cost_usd"]
            bucket["review_cost"] += costs["review_cost_usd"]
            bucket["fallback_cost"] += costs["fallback_cost_usd"]
            bucket["total_cost"] += costs["total_cost_usd"]

    # Write CSV
    path = os.path.join(args.out, "cost_by_baseline.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COST_CSV_COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        for baseline in sorted(by_baseline.keys()):
            b = by_baseline[baseline]
            n = b["n_runs"]
            reviews = b["total_reviews"]
            writer.writerow({
                "baseline": baseline,
                "n_runs": n,
                "total_reviews": reviews,
                "total_cost_usd": f"{b['total_cost']:.6f}",
                "mean_cost_per_task_usd": (
                    f"{b['total_cost'] / n:.6f}" if n > 0 else ""
                ),
                "mean_cost_per_review_usd": (
                    f"{b['total_cost'] / reviews:.6f}" if reviews > 0 else ""
                ),
                "legibility_cost_usd": f"{b['legibility_cost']:.6f}",
                "review_cost_usd": f"{b['review_cost']:.6f}",
                "fallback_cost_usd": f"{b['fallback_cost']:.6f}",
            })

    print(f"Wrote {path} ({len(by_baseline)} baselines)")

    # Print summary
    print(f"\n{'Baseline':<8} {'Runs':>5} {'Reviews':>8} {'Total $':>10} "
          f"{'$/Task':>10} {'$/Review':>10}")
    print("-" * 60)
    for baseline in sorted(by_baseline.keys()):
        b = by_baseline[baseline]
        n = b["n_runs"]
        reviews = b["total_reviews"]
        per_task = b["total_cost"] / n if n > 0 else 0
        per_review = b["total_cost"] / reviews if reviews > 0 else 0
        print(f"{baseline:<8} {n:>5} {reviews:>8} ${b['total_cost']:>9.5f} "
              f"${per_task:>9.6f} ${per_review:>9.6f}")


if __name__ == "__main__":
    main()
