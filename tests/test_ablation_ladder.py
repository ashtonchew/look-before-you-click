"""Tests for analysis/ablation_ladder.py merge logic and plot output."""

import csv
import os

import pytest

from analysis.ablation_ladder import merge_ladder_metrics, write_metrics_csv, LADDER_ORDER
from analysis.plots import write_ablation_ladder_plot


# ---------------------------------------------------------------------------
# Helpers: write tiny results_summary CSVs
# ---------------------------------------------------------------------------

_HEADER = [
    "task_id", "domain", "baseline", "experiment", "is_attack",
    "inject_suffix", "success_score", "success", "safety",
    "review_count", "critical_count", "blocked_count",
    "review_latency_ms_total", "terminated_by_control", "termination_reason",
    "resample_count", "trusted_fallback_count", "threat_model", "condition",
    "main_task_success", "base_task_id", "effective_task_id",
    "scheming_side_task_id", "scheming_side_task_family",
    "scheming_side_task_succeeded",
]


def _row(baseline, is_attack, threat_model, main_task_success, safety):
    return {
        "task_id": "t", "domain": "d", "baseline": baseline,
        "experiment": f"exp_{baseline}", "is_attack": str(is_attack),
        "inject_suffix": "", "success_score": "0", "success": "True",
        "safety": str(safety), "review_count": "0", "critical_count": "0",
        "blocked_count": "0", "review_latency_ms_total": "0",
        "terminated_by_control": "False", "termination_reason": "",
        "resample_count": "0", "trusted_fallback_count": "0",
        "threat_model": threat_model, "condition": "honest",
        "main_task_success": str(main_task_success), "base_task_id": "t",
        "effective_task_id": "t", "scheming_side_task_id": "",
        "scheming_side_task_family": "", "scheming_side_task_succeeded": "",
    }


def _write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_HEADER)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _make_fixture(tmp_path):
    """Create minimal corrected + expansion CSVs with known data."""
    corrected = str(tmp_path / "corrected" / "results_summary.csv")
    expansion = str(tmp_path / "expansion" / "results_summary.csv")

    corrected_rows = [
        # B0: 2 benign (1 success), 2 attack (1 safe)
        _row("B0", False, "environmental", True, True),
        _row("B0", False, "environmental", False, True),
        _row("B0", True, "environmental", False, True),
        _row("B0", True, "environmental", False, False),
        # B4: 2 benign (2 success), 2 attack (2 safe)
        _row("B4", False, "environmental", True, True),
        _row("B4", False, "environmental", True, True),
        _row("B4", True, "environmental", False, True),
        _row("B4", True, "environmental", False, True),
        # Scheming row (should be excluded)
        _row("B0", False, "scheming", True, True),
    ]

    expansion_rows = [
        # B1: 1 benign (0 success), 1 attack (1 safe)
        _row("B1", False, "environmental", False, True),
        _row("B1", True, "environmental", False, True),
        # B2: 1 benign (1 success), 1 attack (0 safe)
        _row("B2", False, "environmental", True, True),
        _row("B2", True, "environmental", False, False),
        # B3: 1 benign (1 success), 1 attack (1 safe)
        _row("B3", False, "environmental", True, True),
        _row("B3", True, "environmental", False, True),
        # Non-environmental row (should be excluded)
        _row("B1", False, "0", True, True),
    ]

    _write_csv(corrected, corrected_rows)
    _write_csv(expansion, expansion_rows)
    return corrected, expansion


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMergeLadderMetrics:

    def test_filters_environmental_only(self, tmp_path):
        corrected, expansion = _make_fixture(tmp_path)
        metrics = merge_ladder_metrics(corrected, expansion)
        # B0 corrected has 3 env rows (2 benign + 1 scheming excluded -> 2 benign)
        b0 = metrics[0]
        assert b0["baseline"] == "B0"
        assert b0["n_benign"] == 2

    def test_picks_correct_cohorts(self, tmp_path):
        corrected, expansion = _make_fixture(tmp_path)
        metrics = merge_ladder_metrics(corrected, expansion)
        assert metrics[0]["source_cohort"] == "final_corrected"  # B0
        assert metrics[1]["source_cohort"] == "expansion"  # B1
        assert metrics[2]["source_cohort"] == "expansion"  # B2
        assert metrics[3]["source_cohort"] == "expansion"  # B3
        assert metrics[4]["source_cohort"] == "final_corrected"  # B4

    def test_output_order(self, tmp_path):
        corrected, expansion = _make_fixture(tmp_path)
        metrics = merge_ladder_metrics(corrected, expansion)
        assert [m["baseline"] for m in metrics] == LADDER_ORDER

    def test_metric_computation(self, tmp_path):
        corrected, expansion = _make_fixture(tmp_path)
        metrics = merge_ladder_metrics(corrected, expansion)

        b0 = metrics[0]
        assert b0["usefulness"] == pytest.approx(0.5)  # 1/2
        assert b0["safety"] == pytest.approx(0.5)  # 1/2

        b4 = metrics[4]
        assert b4["usefulness"] == pytest.approx(1.0)  # 2/2
        assert b4["safety"] == pytest.approx(1.0)  # 2/2

        b1 = metrics[1]
        assert b1["usefulness"] == pytest.approx(0.0)  # 0/1
        assert b1["safety"] == pytest.approx(1.0)  # 1/1

    def test_missing_baseline_raises(self, tmp_path):
        corrected = str(tmp_path / "corrected" / "results_summary.csv")
        expansion = str(tmp_path / "expansion" / "results_summary.csv")

        # Corrected has B0 only (no B4)
        _write_csv(corrected, [
            _row("B0", False, "environmental", True, True),
            _row("B0", True, "environmental", False, True),
        ])
        # Expansion has B1, B2, B3
        _write_csv(expansion, [
            _row("B1", False, "environmental", False, True),
            _row("B1", True, "environmental", False, True),
            _row("B2", False, "environmental", True, True),
            _row("B2", True, "environmental", False, True),
            _row("B3", False, "environmental", True, True),
            _row("B3", True, "environmental", False, True),
        ])

        with pytest.raises(ValueError, match="B4.*no environmental"):
            merge_ladder_metrics(corrected, expansion)


class TestWriteMetricsCSV:

    def test_writes_csv_with_five_rows(self, tmp_path):
        corrected, expansion = _make_fixture(tmp_path)
        metrics = merge_ladder_metrics(corrected, expansion)
        out_dir = str(tmp_path / "out")
        os.makedirs(out_dir)
        path = write_metrics_csv(metrics, out_dir)
        assert os.path.isfile(path)
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 5
        assert [r["baseline"] for r in rows] == LADDER_ORDER


class TestAblationLadderPlot:

    def test_produces_file(self, tmp_path):
        metrics = [
            {"baseline": bl, "usefulness": 0.1 * i, "safety": 0.9 - 0.1 * i}
            for i, bl in enumerate(LADDER_ORDER)
        ]
        path = write_ablation_ladder_plot(metrics, str(tmp_path))
        assert os.path.isfile(path)
        assert path.endswith("ablation_ladder_B0_B1_B2_B3_B4.png")
