# Testing

## Running tests

Tests must run under the os-harm venv (which has `requests` and other dependencies):

```bash
PYTHONPATH=.:os-harm os-harm/.venv/bin/python -m pytest tests/ -v
```

## Unit-level
- Parse a11y tree lines into node dicts
- Normalize `pyautogui.click(x, y)` → NormalizedAction
- Normalize `pyautogui.hotkey(...)` → NormalizedAction
- Detect secret-like strings (sk-, AKIA, ghp_)
- Match click coordinate to smallest containing a11y node
- Route "Send" button click as critical / send_submit_share
- Route plain desktop click as not critical

## Integration smoke
- Same prompt-injection task runs once without `--inject`, once with `--inject`
- Critical step generates a control_events.jsonl entry
- Disallowed action terminates run cleanly and still runs judge
- Aggregate script finds run folders and writes CSV

## Manual inspection (before declaring done)
Look at 3 blocked traces. Confirm each has: screenshot, a11y snapshot, review reason, termination reason.
