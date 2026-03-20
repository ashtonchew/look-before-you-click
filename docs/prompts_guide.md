# Prompts Guide

All prompt templates live in `control/prompts.py`. Do not inline prompt strings in other files.

## Legibility prompt
The legibility call asks the untrusted agent model to explain a critical action. Its output is untrusted — it exists only to make mismatches easier for the reviewer to detect.

Input: instruction, screenshot, a11y tree, raw response, normalized action, matched target, recent history.
Output: LegibilityReport schema (see `docs/data_types.md`).

If the legibility call fails, continue without it. Do not terminate.

## Reviewer prompt
The reviewer is trusted. It answers one question: "Given the current screen state, candidate action, and task, should this action be executed?"

Two input modes exist (see `docs/controller_modes.md`):
- `language_only`: no visual context (baseline)
- `state_grounded`: full visual + structural context (main protocol)

Output: ReviewerResult schema — allow/disallow + risk_score + reason + evidence. The reviewer does NOT output controller actions. That's the controller's job.

## Prompt design rules
- Keep prompts self-contained. Each prompt should make sense without reading other prompts.
- Include the output schema in the prompt so the model knows the expected JSON shape.
- Do not ask the reviewer to decide controller actions (allow/resample/fallback). It only says allow or disallow.
- Do not reveal the review rubric to the untrusted agent in any prompt.
