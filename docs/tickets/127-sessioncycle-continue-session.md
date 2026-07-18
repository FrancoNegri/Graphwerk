# 127. `SessionCycle.continue_session(prompt)` and `/api/prompt` wiring

Status: ready
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

A user can send a follow-up prompt into the *same* Claude session instead
of always starting a fresh one — the machinery (`SessionRunner.resume`,
ADR 040) already exists but today only the internal check-failure retry
calls it. This is what makes a design/decision dialogue a real
back-and-forth instead of disconnected one-shot sessions.

## Acceptance criteria

- `SessionCycle.continue_session(prompt) -> dict` (`graphwerk/cycle.py`):
  raises the same `SessionBusyError` as `start()` when not in a terminal
  state; raises `NoSessionToResumeError` (already defined in
  `graphwerk/session.py`) when no prior session id is stored; otherwise
  resets check-cycle bookkeeping the same way `start()` does (attempt,
  check fields) and calls `self.runner.resume(prompt)`, landing in
  `"running"` state exactly like a fresh `start()`.
- When `check_command is None` (no check gate configured), calls
  `self.runner.resume(prompt)` directly, mirroring `start()`'s existing
  bypass branch.
- `PromptRequest` (`graphwerk/server.py`) gains an optional
  `continue_session: bool = False` field; `/api/prompt` dispatches to
  `runner.continue_session(req.prompt)` when true, `runner.start(...)`
  otherwise. A `NoSessionToResumeError` maps to a 409, same status family
  as the existing `SessionBusyError` handling.

## Likely files

- `graphwerk/cycle.py` — `continue_session`.
- `graphwerk/server.py` — `PromptRequest`, `/api/prompt` dispatch.
- `tests/test_cycle.py`, `tests/test_server.py` — busy/no-session/happy-path
  cases for both.

## Out of scope

- Any UI change (ticket 128).
- Changing the internal check-failure auto-resume path — unaffected,
  still calls `runner.resume` directly from `_advance_check_locked`.
