"""Unit tests for reviewer/legibility/fallback schema validation and config merging."""

import json
import os
import tempfile

import pytest

from control.config import load_control_config, merge_cli_overrides
from control.reviewer import (
    _validate_reviewer_result,
    _validate_legibility,
    _validate_trusted_fallback,
)


class TestReviewerValidation:
    def test_valid_allow_passes(self):
        result = {
            "decision": "ALLOW", "risk_score": 0.1,
            "primary_reason": "ok", "evidence": ["safe"],
            "safer_alternative": None,
        }
        assert _validate_reviewer_result(result) is result

    def test_valid_block_passes(self):
        result = {
            "decision": "BLOCK", "risk_score": 0.9,
            "primary_reason": "bad", "evidence": ["malicious"],
            "safer_alternative": "do nothing",
        }
        assert _validate_reviewer_result(result) is result

    def test_valid_resample_passes(self):
        result = {
            "decision": "RESAMPLE", "risk_score": 0.5,
            "primary_reason": "suspicious", "evidence": ["unclear"],
            "safer_alternative": None,
        }
        assert _validate_reviewer_result(result) is result

    def test_valid_defer_passes(self):
        result = {
            "decision": "DEFER_TO_TRUSTED", "risk_score": 0.6,
            "primary_reason": "high impact", "evidence": ["ambiguous"],
            "safer_alternative": None,
        }
        assert _validate_reviewer_result(result) is result

    def test_missing_field_raises(self):
        result = {"decision": "ALLOW"}
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_reviewer_result(result)

    def test_invalid_decision_raises(self):
        result = {
            "decision": "MAYBE", "risk_score": 0.5,
            "primary_reason": "idk", "evidence": [],
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="must be one of"):
            _validate_reviewer_result(result)

    def test_mode_aware_rejects_disallowed_decision(self):
        result = {
            "decision": "RESAMPLE", "risk_score": 0.5,
            "primary_reason": "try again", "evidence": ["x"],
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="not allowed in current mode"):
            _validate_reviewer_result(result, allowed_decisions={"ALLOW", "BLOCK"})

    def test_mode_aware_allows_valid_decision(self):
        result = {
            "decision": "RESAMPLE", "risk_score": 0.5,
            "primary_reason": "try again", "evidence": ["x"],
            "safer_alternative": None,
        }
        assert _validate_reviewer_result(
            result, allowed_decisions={"ALLOW", "RESAMPLE", "BLOCK"}
        ) is result

    def test_string_risk_score_raises(self):
        result = {
            "decision": "ALLOW", "risk_score": "low",
            "primary_reason": "ok", "evidence": [],
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="must be numeric"):
            _validate_reviewer_result(result)

    def test_string_evidence_raises(self):
        result = {
            "decision": "ALLOW", "risk_score": 0.1,
            "primary_reason": "ok", "evidence": "single string",
            "safer_alternative": None,
        }
        with pytest.raises(ValueError, match="must be a list"):
            _validate_reviewer_result(result)


class TestTrustedFallbackValidation:
    def test_valid_action_passes(self):
        result = {
            "action": "pyautogui.click(100, 200)",
            "reason": "safe click",
            "confidence": 0.8,
        }
        assert _validate_trusted_fallback(result) is result

    def test_null_action_passes(self):
        result = {
            "action": None,
            "reason": "unclear what to do",
            "confidence": 0.2,
        }
        assert _validate_trusted_fallback(result) is result

    def test_missing_action_raises(self):
        result = {"reason": "no action", "confidence": 0.5}
        with pytest.raises(ValueError, match="missing required field"):
            _validate_trusted_fallback(result)

    def test_missing_reason_raises(self):
        result = {"action": None, "confidence": 0.5}
        with pytest.raises(ValueError, match="missing required field"):
            _validate_trusted_fallback(result)

    def test_non_string_action_raises(self):
        result = {"action": 123, "reason": "bad", "confidence": 0.5}
        with pytest.raises(ValueError, match="must be str or null"):
            _validate_trusted_fallback(result)

    def test_multi_action_raises(self):
        result = {
            "action": "pyautogui.click(100, 200); pyautogui.press('enter')",
            "reason": "two steps",
            "confidence": 0.7,
        }
        with pytest.raises(ValueError, match="multiple actions"):
            _validate_trusted_fallback(result)

    def test_single_action_with_pyautogui_prefix_passes(self):
        result = {
            "action": "pyautogui.write('hello world')",
            "reason": "type text",
            "confidence": 0.9,
        }
        assert _validate_trusted_fallback(result) is result

    def test_non_numeric_confidence_raises(self):
        result = {"action": None, "reason": "x", "confidence": "high"}
        with pytest.raises(ValueError, match="must be numeric"):
            _validate_trusted_fallback(result)


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


class TestMergeCLIOverrides:
    """Blocker 1: merge_cli_overrides must not overwrite JSON controller_mode
    when --control_mode is not explicitly passed (i.e. control_mode=None)."""

    def test_none_control_mode_preserves_config(self):
        config = {"controller_mode": "allow_or_resample_once"}
        result = merge_cli_overrides(config, control_mode=None)
        assert result["controller_mode"] == "allow_or_resample_once"

    def test_explicit_control_mode_overrides_config(self):
        config = {"controller_mode": "allow_or_resample_once"}
        result = merge_cli_overrides(config, control_mode="allow_or_terminate")
        assert result["controller_mode"] == "allow_or_terminate"

    def test_none_preserves_trusted_fallback_mode(self):
        config = {"controller_mode": "allow_or_trusted_fallback_once"}
        result = merge_cli_overrides(config, control_mode=None)
        assert result["controller_mode"] == "allow_or_trusted_fallback_once"


class TestKeywordsPathResolution:
    """Blocker 6: critical_keywords_path must resolve relative to config file directory."""

    def test_relative_path_resolved_against_config_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_data = {
                "enabled": True,
                "router_mode": "critical_only",
                "controller_mode": "allow_or_terminate",
                "include_visual_context": True,
                "legibility_enabled": False,
                "fail_closed_on_review_error": True,
                "critical_keywords_path": "configs/critical_keywords.json",
            }
            config_path = os.path.join(tmpdir, "my_config.json")
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            loaded = load_control_config(config_path)
            expected = os.path.join(tmpdir, "configs", "critical_keywords.json")
            assert loaded["critical_keywords_path"] == expected
            assert os.path.isabs(loaded["critical_keywords_path"])

    def test_absolute_path_not_modified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_data = {
                "enabled": True,
                "router_mode": "critical_only",
                "controller_mode": "allow_or_terminate",
                "include_visual_context": True,
                "legibility_enabled": False,
                "fail_closed_on_review_error": True,
                "critical_keywords_path": "/absolute/path/keywords.json",
            }
            config_path = os.path.join(tmpdir, "my_config.json")
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            loaded = load_control_config(config_path)
            assert loaded["critical_keywords_path"] == "/absolute/path/keywords.json"

    def test_null_path_not_modified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_data = {
                "enabled": True,
                "router_mode": "critical_only",
                "controller_mode": "allow_or_terminate",
                "include_visual_context": True,
                "legibility_enabled": False,
                "fail_closed_on_review_error": True,
                "critical_keywords_path": None,
            }
            config_path = os.path.join(tmpdir, "my_config.json")
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            loaded = load_control_config(config_path)
            assert loaded["critical_keywords_path"] is None

    def test_shipped_configs_resolve_to_real_keywords_file(self):
        """Verify all shipped control configs resolve critical_keywords_path
        to the actual critical_keywords.json file on disk."""
        configs_dir = os.path.join(os.path.dirname(__file__), "..", "configs")
        keywords_expected = os.path.join(os.path.abspath(configs_dir), "critical_keywords.json")
        assert os.path.isfile(keywords_expected), f"keywords file missing: {keywords_expected}"

        for name in os.listdir(configs_dir):
            if not name.startswith("control_") or not name.endswith(".json"):
                continue
            config_path = os.path.join(configs_dir, name)
            loaded = load_control_config(config_path)
            resolved = loaded["critical_keywords_path"]
            assert resolved is not None, f"{name} has null critical_keywords_path"
            assert os.path.isfile(resolved), (
                f"{name}: resolved path {resolved} does not exist on disk"
            )
