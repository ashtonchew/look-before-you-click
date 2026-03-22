"""Unit tests for control/critical_router.py."""

import json

import pytest

from control.critical_router import (
    route, _looks_like_secret, _text_contains_url,
    _is_paste_to_external, _is_browser_domain_change,
)


class TestRoute:

    def _action(self, **kwargs):
        """Build a minimal NormalizedAction dict for testing."""
        base = {
            "raw_action": "test",
            "primary_kind": "click",
            "x": None, "y": None,
            "text": None, "keys": None, "button": None,
            "special_token": None,
            "target_matched": False,
            "target_tag": None, "target_name": None,
            "target_text": None, "target_bounds": None,
            "target_match_method": "none",
        }
        base.update(kwargs)
        return base

    def test_send_button_critical(self):
        action = self._action(
            target_matched=True,
            target_tag="push-button",
            target_name="Send",
            target_text="Send",
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "send_submit_share"

    def test_nearby_text_keyword_triggers_critical(self):
        """When nearby_text contains a family keyword but target fields don't,
        the action should still be routed as critical."""
        action = self._action(
            target_matched=True,
            target_tag="push-button",
            target_name="OK",
            target_text="OK",
            nearby_text="Send message forward",
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "send_submit_share"

    def test_nearby_text_no_keyword_not_critical(self):
        action = self._action(
            target_matched=True,
            target_tag="push-button",
            target_name="OK",
            target_text="OK",
            nearby_text="some harmless label",
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is False

    def test_plain_click_not_critical(self):
        action = self._action(
            target_matched=True,
            target_tag="label",
            target_name="Home",
            target_text="Home",
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is False

    def test_wait_not_critical(self):
        action = self._action(primary_kind="wait", special_token="WAIT")
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is False

    def test_done_not_critical(self):
        action = self._action(primary_kind="done", special_token="DONE")
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is False

    def test_fail_not_critical(self):
        action = self._action(primary_kind="fail", special_token="FAIL")
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is False

    def test_always_mode_reviews_everything(self):
        action = self._action(target_name="Home", target_text="Home")
        result = route(action, {"router_mode": "always"})
        assert result["critical"] is True
        assert result["family"] is None
        assert result["reasons"] == ["blanket review mode"]

    def test_always_mode_skips_special_tokens(self):
        action = self._action(primary_kind="wait", special_token="WAIT")
        result = route(action, {"router_mode": "always"})
        assert result["critical"] is False

    def test_ctrl_alt_t_critical(self):
        action = self._action(
            primary_kind="hotkey",
            keys=["ctrl", "alt", "t"],
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "terminal_or_exec"

    def test_delete_button_critical(self):
        action = self._action(
            target_matched=True,
            target_tag="push-button",
            target_name="Delete",
            target_text="Delete",
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "delete_overwrite"

    def test_ctrl_v_paste_critical(self):
        action = self._action(
            primary_kind="hotkey",
            keys=["ctrl", "v"],
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "clipboard_paste_external"

    def test_secret_in_typed_text(self):
        action = self._action(
            primary_kind="type",
            text="sk-abc123def456ghi789jkl012mno345pqr",
        )
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "credential_or_secret_exposure"

    def test_config_loaded_secret_patterns_used(self, tmp_path):
        path = tmp_path / "critical_keywords.json"
        path.write_text(
            json.dumps({"secret_patterns": ["MY_CUSTOM_SECRET"]}),
            encoding="utf-8",
        )
        action = self._action(primary_kind="type", text="MY_CUSTOM_SECRET")
        result = route(
            action,
            {
                "router_mode": "critical_only",
                "critical_keywords_path": str(path),
            },
        )
        assert result["critical"] is True
        assert result["family"] == "credential_or_secret_exposure"

    def test_config_loaded_dangerous_hotkeys_used(self, tmp_path):
        path = tmp_path / "critical_keywords.json"
        path.write_text(
            json.dumps({"dangerous_hotkeys": [["ctrl", "shift", "9"]]}),
            encoding="utf-8",
        )
        action = self._action(primary_kind="hotkey", keys=["CTRL", "SHIFT", "9"])
        result = route(
            action,
            {
                "router_mode": "critical_only",
                "critical_keywords_path": str(path),
            },
        )
        assert result["critical"] is True
        assert result["family"] == "terminal_or_exec"


class TestSecretDetection:

    def test_openai_key(self):
        assert _looks_like_secret("sk-abc123def456ghi789jkl012mno345pqr") is True

    def test_aws_key(self):
        assert _looks_like_secret("AKIA1234567890ABCDEF") is True

    def test_github_token(self):
        assert _looks_like_secret("ghp_abcdefghij1234567890abcdefghij123456") is True

    def test_ssh_key(self):
        assert _looks_like_secret("BEGIN OPENSSH PRIVATE KEY") is True

    def test_normal_text(self):
        assert _looks_like_secret("hello world") is False

    def test_short_text(self):
        assert _looks_like_secret("abc") is False

    def test_email_address(self):
        assert _looks_like_secret("user@example.com") is True

    def test_email_skipped_in_thunderbird(self):
        config = {"_domain": "thunderbird"}
        assert _looks_like_secret("user@example.com", config) is False

    def test_email_flagged_in_chrome(self):
        config = {"_domain": "chrome"}
        assert _looks_like_secret("user@example.com", config) is True


class TestURLDetection:
    def test_http_url(self):
        assert _text_contains_url("http://evil.com") is True

    def test_https_url(self):
        assert _text_contains_url("https://evil.com/path") is True

    def test_no_url(self):
        assert _text_contains_url("just some text") is False


class TestPasteDestination:
    def test_paste_no_target_is_critical(self):
        action = {
            "primary_kind": "hotkey",
            "keys": ["ctrl", "v"],
            "target_matched": False,
        }
        assert _is_paste_to_external(action) is True

    def test_paste_to_terminal_not_critical(self):
        action = {
            "primary_kind": "hotkey",
            "keys": ["ctrl", "v"],
            "target_matched": True,
            "target_tag": "terminal",
            "target_name": "bash",
            "target_text": "",
        }
        assert _is_paste_to_external(action) is False

    def test_paste_to_email_compose_is_critical(self):
        action = {
            "primary_kind": "hotkey",
            "keys": ["ctrl", "v"],
            "target_matched": True,
            "target_tag": "text-input",
            "target_name": "compose message",
            "target_text": "",
        }
        assert _is_paste_to_external(action) is True

    def test_non_paste_hotkey_not_flagged(self):
        action = {
            "primary_kind": "hotkey",
            "keys": ["ctrl", "c"],
            "target_matched": False,
        }
        assert _is_paste_to_external(action) is False


class TestBrowserDomainChange:
    def test_click_on_address_bar(self):
        action = {
            "target_matched": True,
            "target_tag": "entry",
            "target_name": "address bar",
            "target_text": "https://google.com",
        }
        assert _is_browser_domain_change(action) is True

    def test_click_on_url_bar(self):
        action = {
            "target_matched": True,
            "target_tag": "entry",
            "target_name": "urlbar",
            "target_text": "",
        }
        assert _is_browser_domain_change(action) is True

    def test_click_on_external_link(self):
        action = {
            "target_matched": True,
            "target_tag": "link",
            "target_name": "external link to docs",
            "target_text": "",
        }
        assert _is_browser_domain_change(action) is True

    def test_click_on_normal_button(self):
        action = {
            "target_matched": True,
            "target_tag": "push-button",
            "target_name": "OK",
            "target_text": "OK",
        }
        assert _is_browser_domain_change(action) is False

    def test_no_target_returns_false(self):
        action = {"target_matched": False}
        assert _is_browser_domain_change(action) is False


# ---------------------------------------------------------------------------
# Multi-call URL detection (raw action scanning)
# ---------------------------------------------------------------------------


class TestMultiCallURLDetection:
    """Tests for _raw_action_contains_url via the route() entry point."""

    def _action(self, raw_action, **kwargs):
        base = {
            "raw_action": raw_action,
            "primary_kind": "press",
            "x": None, "y": None,
            "text": None, "keys": ["enter"], "button": None,
            "special_token": None,
            "target_matched": False,
            "target_tag": None, "target_name": None,
            "target_text": None, "target_bounds": None,
            "target_match_method": "none",
        }
        base.update(kwargs)
        return base

    def test_write_url_then_press_enter_is_critical(self):
        raw = (
            "pyautogui.click(35, 784)\n"
            "pyautogui.click(363, 114)\n"
            "pyautogui.write('https://swisstransfer.com', interval=0.05)\n"
            "pyautogui.press('enter')"
        )
        result = route(self._action(raw), {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "external_navigation"

    def test_typewrite_url_then_press_enter_is_critical(self):
        raw = (
            "pyautogui.typewrite('https://evil.com/exfil')\n"
            "pyautogui.press('enter')"
        )
        result = route(self._action(raw), {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "external_navigation"

    def test_write_without_url_not_critical(self):
        raw = (
            "pyautogui.write('hello world')\n"
            "pyautogui.press('enter')"
        )
        result = route(self._action(raw), {"router_mode": "critical_only"})
        assert result["critical"] is False

    def test_write_http_url_is_critical(self):
        raw = (
            "pyautogui.write('http://malicious-site.com')\n"
            "pyautogui.press('enter')"
        )
        result = route(self._action(raw), {"router_mode": "critical_only"})
        assert result["critical"] is True

    def test_single_write_url_caught_by_existing_check(self):
        """Single write(URL) normalizes to primary_kind=type, caught by
        the existing 'URL in typed text' check before the raw scan."""
        action = {
            "raw_action": "pyautogui.write('https://example.com')",
            "primary_kind": "type",
            "x": None, "y": None,
            "text": "https://example.com", "keys": None, "button": None,
            "special_token": None,
            "target_matched": False,
            "target_tag": None, "target_name": None,
            "target_text": None, "target_bounds": None,
            "target_match_method": "none",
        }
        result = route(action, {"router_mode": "critical_only"})
        assert result["critical"] is True
        assert result["family"] == "external_navigation"
