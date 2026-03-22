"""Tests for reviewer_ablation screenshot reconstruction logic."""

import json
import os

from analysis.reviewer_ablation import (
    _reconstruct_screenshot,
    _screenshot_from_better_log,
)


PNG_BYTES = b"\x89PNG_FAKE"


def _make_run(tmp_path, pngs, better_log_steps=None):
    """Create a fake run directory with PNGs and optional better_log.json."""
    run_dir = str(tmp_path / "run")
    os.makedirs(run_dir, exist_ok=True)
    for name in pngs:
        with open(os.path.join(run_dir, name), "wb") as f:
            f.write(PNG_BYTES)
    if better_log_steps is not None:
        bl = {"params": {}, "task": {}, "steps": better_log_steps}
        with open(os.path.join(run_dir, "better_log.json"), "w") as f:
            json.dump(bl, f)
    return run_dir


class TestBetterLogLookup:
    def test_exact_match(self, tmp_path):
        run_dir = _make_run(tmp_path,
            pngs=["step_5_20260321@211950.png"],
            better_log_steps=[
                {"screenshot_file": None} for _ in range(5)
            ] + [{"screenshot_file": "step_5_20260321@211950.png"}])
        result = _screenshot_from_better_log(run_dir, 5)
        assert result == PNG_BYTES

    def test_timestamp_fallback(self, tmp_path):
        """better_log says step_10_@212044 but disk has step_9_@212044."""
        run_dir = _make_run(tmp_path,
            pngs=["step_9_20260321@212044.png"],
            better_log_steps=[
                {"screenshot_file": None} for _ in range(10)
            ] + [{"screenshot_file": "step_10_20260321@212044.png"}])
        result = _screenshot_from_better_log(run_dir, 10)
        assert result == PNG_BYTES

    def test_no_better_log_returns_none(self, tmp_path):
        run_dir = _make_run(tmp_path, pngs=["step_5.png"])
        assert _screenshot_from_better_log(run_dir, 5) is None

    def test_step_out_of_range_returns_none(self, tmp_path):
        run_dir = _make_run(tmp_path,
            pngs=["step_0.png"],
            better_log_steps=[{"screenshot_file": "step_0.png"}])
        assert _screenshot_from_better_log(run_dir, 99) is None

    def test_null_screenshot_field_returns_none(self, tmp_path):
        run_dir = _make_run(tmp_path,
            pngs=["step_5.png"],
            better_log_steps=[
                {"screenshot_file": None} for _ in range(6)
            ])
        assert _screenshot_from_better_log(run_dir, 5) is None


class TestReconstructScreenshot:
    def test_better_log_preferred_over_heuristic(self, tmp_path):
        """When better_log maps step 8 to step_5_@211950 (via timestamp),
        the heuristic would pick step_9 (closer by number). Better_log wins."""
        run_dir = _make_run(tmp_path,
            pngs=["step_5_20260321@211950.png", "step_9_20260321@212044.png"],
            better_log_steps=[
                {"screenshot_file": None} for _ in range(8)
            ] + [{"screenshot_file": "step_8_20260321@211950.png"}])
        # Write different content to distinguish which was selected
        with open(os.path.join(run_dir, "step_5_20260321@211950.png"), "wb") as f:
            f.write(b"CORRECT")
        with open(os.path.join(run_dir, "step_9_20260321@212044.png"), "wb") as f:
            f.write(b"WRONG")
        result = _reconstruct_screenshot(run_dir, 8)
        assert result == b"CORRECT"

    def test_heuristic_fallback_no_better_log(self, tmp_path):
        run_dir = _make_run(tmp_path, pngs=["step_5.png", "step_10.png"])
        result = _reconstruct_screenshot(run_dir, 10)
        assert result == PNG_BYTES

    def test_heuristic_respects_drift_limit(self, tmp_path):
        run_dir = _make_run(tmp_path, pngs=["step_0.png"])
        assert _reconstruct_screenshot(run_dir, 20) is None

    def test_no_pngs_returns_none(self, tmp_path):
        run_dir = _make_run(tmp_path, pngs=[])
        assert _reconstruct_screenshot(run_dir, 0) is None
