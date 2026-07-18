# 122. `SessionCycle.status()` always reports `check_configured`

Status: done
Decision: docs/decisions/045-persistent-checks-status-and-naming.md

## Goal

Every `SessionCycle.status()` payload (and `start()`'s return, which reuses
the same shape) carries an explicit `check_configured: bool`, so the
frontend can distinguish "no `--check` command was given" from any other
state instead of inferring it from field presence.

## Acceptance criteria

- When `check_command is None`: `status()` returns the underlying
  `SessionRunner.status()` payload unchanged in every other respect, plus
  `check_configured: False`.
- When `check_command` is set: `status()`'s payload includes
  `check_configured: True`, alongside the existing `attempt`,
  `check_exit_code`, `check_tail`, `check_summary`, `check_duration_s`
  fields (unchanged behavior).
- `start()`'s return value carries the same field (it already returns
  `self._status_locked()` or `self.runner.start(prompt)` depending on the
  same branch).

## Likely files

- `graphwerk/cycle.py` — `status()`'s `check_command is None` branch and
  `_status_locked()`.
- `tests/test_cycle.py` — payload includes `check_configured` true/false in
  both branches.

## Out of scope

- Frontend consumption of the new field (ticket 123).
- Any change to when/how the cycle transitions state.
