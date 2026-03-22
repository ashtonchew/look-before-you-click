# Failure Handling

These rules are strict. Do not improvise alternatives.

| Failure | Action | Terminate? |
|---|---|---|
| Review model errors on critical action | Fail closed, log `review_error_fail_closed` | Yes |
| Legibility call fails | Continue with `legibility_report = null`, log error | No |
| A11y parsing fails | Continue with raw a11y text, set target = null | No |
| Judge fails after run | Mark judge output missing, keep run output | No |
| Agent outputs unparsable action | Log parse error | Yes |

Never silently recover or "fix" broken output. Be loud about errors.
