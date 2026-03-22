"""Concentration analysis: compute action family counts and failure taxonomy.

Usage:
    python -m analysis.concentration --annotations analysis_inputs/concentration_annotations.csv --out analysis_outputs
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

_project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from analysis.aggregate import read_control_events  # noqa: E402
from analysis.plots import write_failure_taxonomy_plot  # noqa: E402


# ---------------------------------------------------------------------------
# Annotation loading
# ---------------------------------------------------------------------------

VALID_THREAT_MODELS = {"environmental", "scheming"}
VALID_OUTCOMES = {"harm_succeeded", "harm_near_miss", "harm_blocked", "attack_abandoned"}
BOOL_FIELDS = ["screen_evidence", "a11y_evidence", "legibility_mismatch", "history_evidence"]


def load_annotations(path: str) -> list[dict]:
    """Load and validate the concentration annotations CSV."""
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    validated = []
    for i, row in enumerate(rows):
        if row.get("threat_model") not in VALID_THREAT_MODELS:
            print(f"WARNING: row {i+1} has invalid threat_model: {row.get('threat_model')!r}, skipping")
            continue
        if row.get("outcome") not in VALID_OUTCOMES:
            print(f"WARNING: row {i+1} has invalid outcome: {row.get('outcome')!r}, skipping")
            continue
        for bf in BOOL_FIELDS:
            if row.get(bf, "").lower() not in ("yes", "no", ""):
                print(f"WARNING: row {i+1} has invalid {bf}: {row.get(bf)!r}")
        validated.append(row)
    return validated


# ---------------------------------------------------------------------------
# Count computations
# ---------------------------------------------------------------------------

def compute_family_counts(annotations: list[dict], all_events: dict[str, list[dict]]) -> list[dict]:
    """Count by action family from annotations + router events."""
    counts = defaultdict(lambda: {"annotated": 0, "routed": 0, "blocked": 0, "reviewed": 0})

    for ann in annotations:
        family = ann.get("action_family", "").strip()
        if family:
            counts[family]["annotated"] += 1

    for events in all_events.values():
        for event in events:
            router = event.get("router_decision", {})
            family = router.get("family")
            if family and router.get("critical"):
                counts[family]["routed"] += 1
                counts[family]["reviewed"] += 1
                controller = event.get("controller_decision", {})
                if not controller.get("execute", True):
                    counts[family]["blocked"] += 1

    return [{"family": f, **c} for f, c in sorted(counts.items(), key=lambda x: -x[1]["annotated"])]


def compute_failure_taxonomy(annotations: list[dict]) -> list[dict]:
    """Group annotations by (failure_mode, outcome, threat_model).

    Each row has exactly one threat_model, so downstream aggregation
    does not need to redistribute counts across threat models.
    """
    groups = defaultdict(lambda: {"count": 0, "example_task_ids": []})
    for ann in annotations:
        fm = ann.get("failure_mode", "").strip() or "unspecified"
        outcome = ann.get("outcome", "")
        tm = ann.get("threat_model", "")
        key = (fm, outcome, tm)
        groups[key]["count"] += 1
        tid = ann.get("task_id", "")
        if tid and tid not in groups[key]["example_task_ids"]:
            groups[key]["example_task_ids"].append(tid)

    result = []
    for (fm, outcome, tm), data in sorted(groups.items(), key=lambda x: -x[1]["count"]):
        result.append({
            "failure_mode": fm,
            "outcome": outcome,
            "count": data["count"],
            "threat_model": tm,
            "example_task_id": data["example_task_ids"][0] if data["example_task_ids"] else "",
        })
    return result


def taxonomy_to_plot_data(taxonomy: list[dict]) -> dict[str, dict[str, int]]:
    """Convert taxonomy rows to the nested dict expected by write_failure_taxonomy_plot.

    Aggregates across outcomes per (failure_mode, threat_model).
    Each taxonomy row already has a single threat_model, so counts are
    added directly without redistribution.
    """
    result: dict[str, dict[str, int]] = {}
    for row in taxonomy:
        fm = row["failure_mode"]
        count = row["count"]
        tm = row.get("threat_model", "")
        if not tm:
            continue
        if fm not in result:
            result[fm] = {}
        result[fm][tm] = result[fm].get(tm, 0) + count
    return result


def compute_trace_summary(annotations: list[dict]) -> list[dict]:
    """Per-trace summary row."""
    summaries = []
    for ann in annotations:
        evidence_flags = []
        for bf in BOOL_FIELDS:
            if ann.get(bf, "").lower() == "yes":
                evidence_flags.append(bf)
        summaries.append({
            "run_dir": ann.get("run_dir", ""),
            "threat_model": ann.get("threat_model", ""),
            "baseline": ann.get("baseline", ""),
            "task_id": ann.get("task_id", ""),
            "outcome": ann.get("outcome", ""),
            "decisive_step": ann.get("decisive_step", ""),
            "action_family": ann.get("action_family", ""),
            "irreversible": ann.get("irreversible", ""),
            "evidence_flags": ",".join(evidence_flags),
            "failure_mode": ann.get("failure_mode", ""),
        })
    return summaries


def compute_blocked_family_counts(all_events: dict[str, list[dict]]) -> list[dict]:
    """Counts by blocked action family from control_events.jsonl."""
    counts = Counter()
    for events in all_events.values():
        for event in events:
            router = event.get("router_decision", {})
            family = router.get("family")
            controller = event.get("controller_decision", {})
            if family and not controller.get("execute", True):
                counts[family] += 1
    return [{"family": f, "blocked_count": c} for f, c in counts.most_common()]


def compute_reviewer_decision_counts(all_events: dict[str, list[dict]]) -> list[dict]:
    """Counts by reviewer decision type from control_events.jsonl."""
    counts = Counter()
    for events in all_events.values():
        for event in events:
            reviewer = event.get("reviewer_result")
            if reviewer is not None:
                decision = reviewer.get("decision")
                if not decision and "allow" in reviewer:
                    decision = "ALLOW" if reviewer["allow"] else "BLOCK"
                if decision:
                    counts[decision] += 1
    return [{"decision": d, "count": c} for d, c in counts.most_common()]


def compute_action_source_counts(all_events: dict[str, list[dict]]) -> list[dict]:
    """Counts by final_action_source from control_events.jsonl."""
    counts = Counter()
    for events in all_events.values():
        for event in events:
            source = event.get("final_action_source")
            if source:
                counts[source] += 1
    return [{"action_source": s, "count": c} for s, c in counts.most_common()]


def compute_threat_model_counts(annotations: list[dict]) -> list[dict]:
    """Counts by threat model from annotations."""
    counts = Counter(a.get("threat_model", "") for a in annotations)
    return [{"threat_model": tm, "count": c} for tm, c in counts.most_common()]


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def write_family_counts_csv(counts: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_family_counts.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["family", "annotated", "routed", "blocked", "reviewed"])
        w.writeheader()
        w.writerows(counts)
    print(f"Wrote {path} ({len(counts)} families)")
    return path


def write_failure_taxonomy_csv(taxonomy: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_failure_taxonomy.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["failure_mode", "outcome", "count",
                                           "threat_model", "example_task_id"])
        w.writeheader()
        w.writerows(taxonomy)
    print(f"Wrote {path} ({len(taxonomy)} groups)")
    return path


def write_blocked_family_counts_csv(counts: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_blocked_family_counts.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["family", "blocked_count"])
        w.writeheader()
        w.writerows(counts)
    print(f"Wrote {path} ({len(counts)} families)")
    return path


def write_reviewer_decision_counts_csv(counts: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_reviewer_decision_counts.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["decision", "count"])
        w.writeheader()
        w.writerows(counts)
    print(f"Wrote {path} ({len(counts)} decisions)")
    return path


def write_action_source_counts_csv(counts: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_action_source_counts.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["action_source", "count"])
        w.writeheader()
        w.writerows(counts)
    print(f"Wrote {path} ({len(counts)} sources)")
    return path


def write_threat_model_counts_csv(counts: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_threat_model_counts.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["threat_model", "count"])
        w.writeheader()
        w.writerows(counts)
    print(f"Wrote {path} ({len(counts)} threat models)")
    return path


def write_trace_summary_csv(summaries: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "concentration_trace_summary.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run_dir", "threat_model", "baseline", "task_id",
                                           "outcome", "decisive_step", "action_family",
                                           "irreversible", "evidence_flags", "failure_mode"])
        w.writeheader()
        w.writerows(summaries)
    print(f"Wrote {path} ({len(summaries)} traces)")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Concentration analysis")
    parser.add_argument("--annotations", required=True, help="Path to concentration_annotations.csv")
    parser.add_argument("--out", default="analysis_outputs", help="Output directory")
    args = parser.parse_args()

    annotations = load_annotations(args.annotations)
    if not annotations:
        print("No valid annotations found. Populate the annotations CSV first.")
        return

    # Load control events for all annotated run directories
    all_events = {}
    for ann in annotations:
        run_dir = ann.get("run_dir", "").strip()
        if run_dir and run_dir not in all_events:
            all_events[run_dir] = read_control_events(run_dir)

    os.makedirs(args.out, exist_ok=True)

    family_counts = compute_family_counts(annotations, all_events)
    write_family_counts_csv(family_counts, args.out)

    taxonomy = compute_failure_taxonomy(annotations)
    write_failure_taxonomy_csv(taxonomy, args.out)

    plot_data = taxonomy_to_plot_data(taxonomy)
    plot_path = write_failure_taxonomy_plot(plot_data, args.out)
    if plot_path:
        print(f"Wrote {plot_path}")

    trace_summaries = compute_trace_summary(annotations)
    write_trace_summary_csv(trace_summaries, args.out)

    # Automatic counts from control events
    blocked_counts = compute_blocked_family_counts(all_events)
    write_blocked_family_counts_csv(blocked_counts, args.out)

    reviewer_counts = compute_reviewer_decision_counts(all_events)
    write_reviewer_decision_counts_csv(reviewer_counts, args.out)

    source_counts = compute_action_source_counts(all_events)
    write_action_source_counts_csv(source_counts, args.out)

    tm_counts = compute_threat_model_counts(annotations)
    write_threat_model_counts_csv(tm_counts, args.out)

    # Print summary
    print(f"\nAnnotated traces: {len(annotations)}")
    by_tm = Counter(a["threat_model"] for a in annotations)
    for tm, n in sorted(by_tm.items()):
        print(f"  {tm}: {n}")
    by_outcome = Counter(a["outcome"] for a in annotations)
    for outcome, n in sorted(by_outcome.items()):
        print(f"  {outcome}: {n}")


if __name__ == "__main__":
    main()
