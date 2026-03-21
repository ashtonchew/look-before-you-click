"""Unit tests for reviewer/legibility schema validation."""

import pytest

from control.reviewer import _validate_reviewer_result, _validate_legibility


class TestReviewerValidation:
    def test_valid_result_passes(self):
        result = {
            "allow": True, "risk_score": 0.1,
            "primary_reason": "ok", "evidence": ["safe"],
            "safer_alternative": None,
        }
        assert _validate_reviewer_result(result) is result

    def test_missing_field_raises(self):
        result = {"allow": True}
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_reviewer_result(result)

    def test_string_allow_raises(self):
        result = {
            "allow": "false", "risk_score": 0.9,
            "primary_reason": "bad", "evidence": ["x"],
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="must be bool"):
            _validate_reviewer_result(result)

    def test_string_risk_score_raises(self):
        result = {
            "allow": True, "risk_score": "low",
            "primary_reason": "ok", "evidence": [],
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="must be numeric"):
            _validate_reviewer_result(result)

    def test_string_evidence_raises(self):
        result = {
            "allow": True, "risk_score": 0.1,
            "primary_reason": "ok", "evidence": "single string",
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="must be a list"):
            _validate_reviewer_result(result)


class TestLegibilityValidation:
    def test_empty_fills_none(self):
        result = _validate_legibility({})
        assert result["action_type"] is None
        assert result["confidence"] is None
        assert len(result) == 8

    def test_existing_fields_preserved(self):
        result = _validate_legibility({"action_type": "click", "confidence": 0.9})
        assert result["action_type"] == "click"
        assert result["confidence"] == 0.9
