"""Unit tests for control/action_normalizer.py."""

import pytest

from control.action_normalizer import normalize


class TestNormalize:

    def test_click_positional(self):
        result = normalize("pyautogui.click(100, 200)")
        assert result["primary_kind"] == "click"
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["special_token"] is None

    def test_click_keyword_args(self):
        result = normalize("pyautogui.click(x=300, y=400, button='right')")
        assert result["primary_kind"] == "click"
        assert result["x"] == 300
        assert result["y"] == 400
        assert result["button"] == "right"

    def test_double_click(self):
        result = normalize("pyautogui.doubleClick(50, 60)")
        assert result["primary_kind"] == "double_click"
        assert result["x"] == 50
        assert result["y"] == 60

    def test_right_click(self):
        result = normalize("pyautogui.rightClick(70, 80)")
        assert result["primary_kind"] == "right_click"

    def test_hotkey(self):
        result = normalize("pyautogui.hotkey('ctrl', 'c')")
        assert result["primary_kind"] == "hotkey"
        assert result["keys"] == ["ctrl", "c"]
        assert result["x"] is None

    def test_hotkey_three_keys(self):
        result = normalize("pyautogui.hotkey('ctrl', 'alt', 't')")
        assert result["primary_kind"] == "hotkey"
        assert result["keys"] == ["ctrl", "alt", "t"]

    def test_typewrite(self):
        result = normalize("pyautogui.typewrite('source ~/.bashrc')")
        assert result["primary_kind"] == "type"
        assert result["text"] == "source ~/.bashrc"

    def test_write(self):
        result = normalize("pyautogui.write('hello')")
        assert result["primary_kind"] == "type"
        assert result["text"] == "hello"

    def test_press(self):
        result = normalize("pyautogui.press('enter')")
        assert result["primary_kind"] == "press"
        assert result["keys"] == ["enter"]

    def test_scroll(self):
        result = normalize("pyautogui.scroll(-3)")
        assert result["primary_kind"] == "scroll"

    def test_drag_to(self):
        result = normalize("pyautogui.dragTo(100, 200)")
        assert result["primary_kind"] == "drag"
        assert result["x"] == 100

    def test_special_token_wait(self):
        result = normalize("WAIT")
        assert result["primary_kind"] == "wait"
        assert result["special_token"] == "WAIT"

    def test_special_token_done(self):
        result = normalize("DONE")
        assert result["primary_kind"] == "done"
        assert result["special_token"] == "DONE"

    def test_special_token_fail(self):
        result = normalize("FAIL")
        assert result["primary_kind"] == "fail"
        assert result["special_token"] == "FAIL"

    def test_unparsable(self):
        with pytest.raises(ValueError, match="no pyautogui calls"):
            normalize("some random text")

    def test_multi_line_with_imports(self):
        """Real trace: multi-line code with import, comment, click, sleep."""
        raw = (
            "import pyautogui, time\n\n"
            "# Click the \"Show Applications\" grid button\n"
            "pyautogui.click(35, 871)\n"
            "time.sleep(0.5)"
        )
        result = normalize(raw)
        assert result["primary_kind"] == "click"
        assert result["x"] == 35
        assert result["y"] == 871

    def test_moveto_then_click_inherits_coords(self):
        raw = "pyautogui.moveTo(500, 300)\npyautogui.click()"
        result = normalize(raw)
        assert result["primary_kind"] == "click"
        assert result["x"] == 500
        assert result["y"] == 300

    def test_multi_primitive_last_impactful(self):
        """Multiple calls -- pick the last impactful one."""
        raw = (
            "pyautogui.click(100, 200)\n"
            "pyautogui.typewrite('hello')\n"
        )
        result = normalize(raw)
        assert result["primary_kind"] == "type"
        assert result["text"] == "hello"

    def test_real_trace_typewrite_and_press(self):
        """Real trace: typewrite then press enter."""
        raw = (
            "import pyautogui, time\n\n"
            "# Focus the terminal\n"
            "pyautogui.click(1200, 500)\n"
            "time.sleep(0.5)\n\n"
            "# Reload .bashrc\n"
            "pyautogui.typewrite('source ~/.bashrc')\n"
            "pyautogui.press('enter')\n"
            "time.sleep(0.5)"
        )
        result = normalize(raw)
        # Last impactful is press('enter')
        assert result["primary_kind"] == "press"
        assert result["keys"] == ["enter"]
