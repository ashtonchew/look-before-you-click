"""Tests for control/prompts.py visual context construction."""

import json

from control.prompts import build_visual_context


class TestBuildVisualContext:
    def test_empty_when_no_a11y_and_no_legibility(self):
        assert build_visual_context("", None) == ""
        assert build_visual_context(None, None) == ""

    def test_empty_when_no_a11y_even_with_legibility(self):
        """Runtime contract: no a11y tree means no visual context, even if
        legibility is present. Ablation uses a separate path."""
        report = {"action_type": "click", "confidence": 0.9}
        assert build_visual_context("", report) == ""
        assert build_visual_context(None, report) == ""

    def test_includes_a11y_tree(self):
        result = build_visual_context("button 'Submit'", None)
        assert "button 'Submit'" in result
        assert "Screen state" in result

    def test_includes_both_a11y_and_legibility(self):
        report = {"action_type": "click", "target_element": "Submit"}
        result = build_visual_context("button 'Submit'", report)
        assert "button 'Submit'" in result
        assert "action_type" in result
        assert "self-explanation" in result

    def test_truncates_long_a11y_tree(self):
        long_tree = "x" * 10000
        result = build_visual_context(long_tree, None)
        # Should be truncated to 5000 chars within the block
        assert len(result) < 6000
