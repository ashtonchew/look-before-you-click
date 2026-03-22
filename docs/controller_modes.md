# Controller Modes

The reviewer only says allow/disallow. The controller mode decides what happens on disallow. This separation is intentional.

## allow_or_terminate (MVP default)
- Reviewer allows → execute action
- Reviewer disallows → terminate run, log reason, still run judge

## allow_or_resample_once (stretch)
- Reviewer disallows → ask agent for ONE replacement on same state
- Replacement also disallowed → terminate
- Max 1 resample per step. No loops. Do not reveal review rubric to untrusted agent.

## allow_or_trusted_fallback_once (stretch)
- Reviewer disallows → ask trusted model for ONE replacement action
- Fallback can't act confidently → terminate

## Termination semantics
When terminating on a blocked critical action: end recording, write control termination record, still run post-run judge, mark run as blocked in control summary.

## Reviewer input modes
- `language_only` (baseline): instruction, raw response, normalized action, recent history. No screenshot, no a11y.
- `state_grounded` (main protocol): adds screenshot, a11y tree, matched target, trusted facts, legibility report.
