# 120. `SessionCycle` propagates the check summary and names failures on resume

Status: done
Decision: docs/decisions/044-check-result-summary-reporting.md

## Goal

`SessionCycle`'s status payload carries the structured check summary from
ticket 119, and the auto-resume prompt names specific failing tests when
they're known — closing the gap where the bounded output tail can drop
earlier failures on a many-failure run.

## Acceptance criteria

- `status()`'s payload includes `check_summary` (dict or `None`) and
  `check_duration_s`, sourced from the underlying `CheckRunner` result.
- When a check fails and a retry is attempted, and `check_summary` has a
  non-empty `failures` list, the resume prompt sent via `runner.resume()`
  explicitly lists those failing test identifiers and notes the tail below
  may not show all of them.
- When a check fails with no summary (or a summary with no `failures`
  list), the resume prompt is byte-for-byte the same as today's
  `FAILURE_PROMPT_TEMPLATE` output — no regression for operators who don't
  opt into the summary file.

## Likely files

- `graphwerk/cycle.py` — carry the new fields through `_status_locked()`;
  extend the resume-prompt construction in `_advance_check_locked()`.
- `tests/test_cycle.py` — payload includes new fields; resume prompt
  content with/without a `failures` list.

## Out of scope

- `CheckRunner`'s own parsing (ticket 119, already done).
- UI rendering (ticket 121).
- `/api/session` — payload fields flow through unchanged since it already
  forwards the cycle's `status()` dict as-is.
