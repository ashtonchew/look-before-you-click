# Data Types

All types are plain dicts or dataclasses. No metaclasses, no inheritance.

## NormalizedAction
Unified representation of pyautogui or computer_13 actions.
- `raw_action`: str | dict
- `raw_format`: "pyautogui" | "computer_13" | "special"
- `primary_kind`: click | double_click | right_click | type | press | hotkey | scroll | drag | wait | done | fail | other
- `sub_actions`: list of parsed primitives if snippet contains multiple
- `x`, `y`: float | null
- `text`: str | null
- `keys`: list[str] | null
- `button`: str | null
- `special_token`: WAIT | DONE | FAIL | null

## ObservationSnapshot
- `screenshot_bytes`, `a11y_tree_raw`, `a11y_tree_linearized`, `step_index`, `task_id`, `domain`

## A11yTarget
- `matched`: bool
- `tag`, `name`, `text`, `class`, `description`: str | null
- `bounds`: {x, y, w, h} | null
- `match_method`: contains_point | nearest_center | none

## RouterDecision
- `critical`: bool
- `family`: str | null (from taxonomy in `docs/critical_action_taxonomy.md`)
- `reasons`: list[str]
- `confidence`: float

## LegibilityReport
Generated only for critical actions if legibility is enabled.
- `action_type`, `target_element`, `target_text_or_label`
- `why_needed_for_user_goal`, `expected_visible_effect_next`, `what_could_go_wrong`
- `security_relevance`: low | medium | high
- `confidence`: float

## TrustedFacts
Deterministic extraction, no LLM call.
- `target_node_name`, `target_node_text`, `target_node_class`: str | null
- `danger_terms`, `url_candidates`, `email_candidates`, `file_candidates`: list[str]

## ReviewPackage
Sent to trusted reviewer. Contains: instruction, raw_response, normalized_action, router_decision, observation, target, trusted_facts, legibility_report (if available), recent_history.

## ReviewerResult
- `allow`: bool
- `risk_score`: float
- `primary_reason`: str
- `evidence`: list[str]
- `safer_alternative`: str | null

## ControllerDecision
Runtime uses this to decide execution.
- `execute`: bool
- `action_to_execute`: str | dict | null
- `termination_reason`: str | null
- `resample_requested`, `trusted_fallback_requested`: bool

## ControlEventLog
One JSONL record per reviewed action: task_id, domain, step_index, raw_action, normalized_action, router_decision, legibility_report, trusted_facts, reviewer_result, controller_decision, review_latency_ms, reviewer_model.
