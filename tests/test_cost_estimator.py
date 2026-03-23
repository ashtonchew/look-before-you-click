"""Tests for analysis/cost_estimator.py."""

import csv
import json
import os

import pytest

from analysis.cost_estimator import (
    MODEL_PRICING,
    screenshot_tokens,
    estimate_event_cost,
    estimate_run_cost,
    _token_cost,
)


class TestScreenshotTokens:

    def test_gpt4o_mini_tile_formula(self):
        # 1920x985 -> scale shortest=985 to 768 -> 1498x768
        # tiles = ceil(1498/512)*ceil(768/512) = 3*2 = 6
        # 85 + 170*6 = 1105
        assert screenshot_tokens(1920, 985, "gpt-4o-mini") == 1105

    def test_gpt4o_tile_formula(self):
        assert screenshot_tokens(1920, 985, "gpt-4o") == 1105

    def test_gpt5_mini_patch_formula_capped(self):
        # 1920x985 -> ceil(1920/32)*ceil(985/32) = 60*31 = 1860 -> capped at 1536
        assert screenshot_tokens(1920, 985, "gpt-5.4-mini") == 1536

    def test_small_image_under_cap(self):
        # 640x480 -> ceil(640/32)*ceil(480/32) = 20*15 = 300
        assert screenshot_tokens(640, 480, "gpt-5.4-mini") == 300

    def test_exact_cap_boundary(self):
        # Find dimensions that give exactly 1536 patches
        # 1024x1536 -> 32*48 = 1536 exactly
        assert screenshot_tokens(1024, 1536, "gpt-5.4-mini") == 1536

    def test_unknown_model_uses_patch_formula(self):
        # Unknown models default to patch formula
        assert screenshot_tokens(640, 480, "future-model") == 300

    def test_default_args(self):
        # Default is 1920x985 with gpt-5.4-mini
        assert screenshot_tokens() == 1536


class TestTokenCost:

    def test_known_model(self):
        cost = _token_cost("gpt-5.4-mini", 1000, 1000)
        # 1000/1000 * 0.00075 + 1000/1000 * 0.0045 = 0.00075 + 0.0045 = 0.00525
        assert cost == pytest.approx(0.00525)

    def test_gpt4o_mini(self):
        cost = _token_cost("gpt-4o-mini", 1000, 1000)
        # 1000/1000 * 0.00015 + 1000/1000 * 0.0006 = 0.00015 + 0.0006 = 0.00075
        assert cost == pytest.approx(0.00075)

    def test_unknown_model_returns_zero(self):
        assert _token_cost("unknown-model", 1000, 1000) == 0.0

    def test_zero_tokens(self):
        assert _token_cost("gpt-5.4-mini", 0, 0) == 0.0


class TestEstimateEventCost:

    def test_no_calls_zero_cost(self):
        event = {
            "legibility_report": None,
            "reviewer_result": None,
            "trusted_fallback_result": None,
        }
        result = estimate_event_cost(event, {})
        assert result["total_cost_usd"] == 0.0
        assert result["legibility_cost_usd"] == 0.0
        assert result["review_cost_usd"] == 0.0
        assert result["fallback_cost_usd"] == 0.0

    def test_review_only_visual(self):
        event = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        summary = {"include_visual_context": True}
        result = estimate_event_cost(event, summary)
        assert result["review_cost_usd"] > 0
        assert result["legibility_cost_usd"] == 0.0
        assert result["fallback_cost_usd"] == 0.0
        assert result["total_cost_usd"] == result["review_cost_usd"]

    def test_review_only_text(self):
        event = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        summary = {"include_visual_context": False}
        result = estimate_event_cost(event, summary)
        assert result["review_cost_usd"] > 0
        # Text-only should be cheaper than visual
        visual_result = estimate_event_cost(event, {"include_visual_context": True})
        assert result["review_cost_usd"] < visual_result["review_cost_usd"]

    def test_review_with_legibility_costs_more(self):
        review_only = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        review_plus_leg = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": {"action_type": "click"},
            "trusted_fallback_result": None,
        }
        summary = {"include_visual_context": True}
        cost_b3 = estimate_event_cost(review_only, summary)["total_cost_usd"]
        cost_b4 = estimate_event_cost(review_plus_leg, summary)["total_cost_usd"]
        assert cost_b4 > cost_b3

    def test_legibility_cost_uses_gpt4o_mini(self):
        event = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": {"action_type": "click"},
            "trusted_fallback_result": None,
        }
        summary = {"include_visual_context": True}
        result = estimate_event_cost(event, summary)
        # Legibility cost should be cheaper than review cost
        assert result["legibility_cost_usd"] < result["review_cost_usd"]

    def test_fallback_cost(self):
        event = {
            "reviewer_result": {"decision": "DEFER_TO_TRUSTED"},
            "legibility_report": None,
            "trusted_fallback_result": {"action": "click(100, 200)"},
        }
        summary = {"include_visual_context": True}
        result = estimate_event_cost(event, summary)
        assert result["fallback_cost_usd"] > 0
        assert result["review_cost_usd"] > 0

    def test_empty_summary_defaults(self):
        event = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        result = estimate_event_cost(event, {})
        # Default: no visual context -> text-only review
        assert result["review_cost_usd"] > 0

    def test_missing_fields_resilient(self):
        # Minimal event dict
        result = estimate_event_cost({}, {})
        assert result["total_cost_usd"] == 0.0


class TestEstimateRunCost:

    def test_empty_events(self):
        assert estimate_run_cost([], {}) == 0.0

    def test_sums_across_events(self):
        event = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        summary = {"include_visual_context": True}
        single = estimate_event_cost(event, summary)["total_cost_usd"]
        total = estimate_run_cost([event, event, event], summary)
        assert total == pytest.approx(single * 3)

    def test_mixed_events(self):
        reviewed = {
            "reviewer_result": {"decision": "ALLOW"},
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        not_reviewed = {
            "reviewer_result": None,
            "legibility_report": None,
            "trusted_fallback_result": None,
        }
        summary = {"include_visual_context": True}
        total = estimate_run_cost([reviewed, not_reviewed], summary)
        single = estimate_event_cost(reviewed, summary)["total_cost_usd"]
        assert total == pytest.approx(single)


class TestModelPricing:

    def test_pricing_keys_exist(self):
        assert "gpt-5.4-mini" in MODEL_PRICING
        assert "gpt-4o-mini" in MODEL_PRICING

    def test_gpt5_more_expensive(self):
        assert MODEL_PRICING["gpt-5.4-mini"]["input"] > MODEL_PRICING["gpt-4o-mini"]["input"]
        assert MODEL_PRICING["gpt-5.4-mini"]["output"] > MODEL_PRICING["gpt-4o-mini"]["output"]
