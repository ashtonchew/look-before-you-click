"""Smoke tests for analysis/aggregate.py -- Group 5 fixes."""

import csv
import json
import os
import tempfile

from analysis.aggregate import (
    infer_baseline,
    read_judgment,
    write_results_csv,
    parse_run_folder,
    CSV_COLUMNS,
)


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def _write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class TestInferBaseline:
    def test_b0_when_no_summary(self):
        assert infer_baseline(None, "/fake") == "B0_none"

    def test_b3_when_legibility_disabled(self):
        summary = {
            "router_mode": "critical_only",
            "include_visual_context": True,
            "legibility_enabled": False,
        }
        assert infer_baseline(summary, "/fake") == "B3_critical"

    def test_b4_from_config_not_events(self):
        """B4 should be detected from legibility_enabled in summary, not event scanning."""
        summary = {
            "router_mode": "critical_only",
            "include_visual_context": True,
            "legibility_enabled": True,
        }
        # Even with a non-existent run_dir (no events to scan), B4 should be detected
        assert infer_baseline(summary, "/nonexistent") == "B4_critical_legibility"

    def test_b1_always_language(self):
        summary = {
            "router_mode": "always",
            "include_visual_context": False,
        }
        assert infer_baseline(summary, "/fake") == "B1_always_language"

    def test_b2_always_visual(self):
        summary = {
            "router_mode": "always",
            "include_visual_context": True,
        }
        assert infer_baseline(summary, "/fake") == "B2_always_visual"


class TestReadJudgment:
    def test_reads_via_adapter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            judgment_path = os.path.join(
                tmpdir, "judgment", "gpt-4.1", "aer", "v3", "judgment.json"
            )
            _write_json(judgment_path, {
                "success": True,
                "safety": False,
                "violation_step": 3,
                "reasoning": "test reason",
            })
            result = read_judgment(tmpdir, "gpt-4.1", "aer", "v3")
            assert result is not None
            assert result["judge_success"] is True
            assert result["judge_safety"] is False
            assert result["judge_violation_step"] == 3
            assert "judge_reasoning" not in result

    def test_returns_none_when_missing(self):
        result = read_judgment("/nonexistent", "gpt-4.1", "aer", "v3")
        assert result is None


class TestCSVColumns:
    def test_canonical_column_names(self):
        assert "success_score" in CSV_COLUMNS
        assert "success" in CSV_COLUMNS
        assert "safety" in CSV_COLUMNS
        assert "result" not in CSV_COLUMNS
        assert "judge_success" not in CSV_COLUMNS
        assert "judge_safety" not in CSV_COLUMNS

    def test_write_results_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs = [{
                "task_id": "t1",
                "domain": "chrome",
                "baseline": "B3_critical",
                "experiment": "exp1",
                "is_attack": False,
                "success_score": 1.0,
                "success": True,
                "safety": None,
                "review_count": 2,
                "critical_count": 3,
                "blocked_count": 0,
                "review_latency_ms_total": 500,
                "terminated_by_control": False,
                "termination_reason": None,
            }]
            path = write_results_csv(runs, tmpdir)
            with open(path) as f:
                reader = csv.DictReader(f)
                row = next(reader)
                assert row["success_score"] == "1.0"
                assert row["success"] == "True"


class TestConfigValidation:
    def test_all_configs_valid_json_with_keywords_path(self):
        configs_dir = os.path.join(os.path.dirname(__file__), "..", "configs")
        for name in os.listdir(configs_dir):
            if not name.startswith("control_") or not name.endswith(".json"):
                continue
            path = os.path.join(configs_dir, name)
            with open(path) as f:
                cfg = json.load(f)
            assert "critical_keywords_path" in cfg, f"{name} missing critical_keywords_path"

    def test_critical_keywords_json_valid(self):
        path = os.path.join(os.path.dirname(__file__), "..", "configs", "critical_keywords.json")
        with open(path) as f:
            data = json.load(f)
        assert "family_keywords" in data
        assert "secret_patterns" in data
        assert "dangerous_hotkeys" in data
