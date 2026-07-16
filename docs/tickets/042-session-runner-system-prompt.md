# 042. `SessionRunner` gains a `system_prompt` parameter

Status: done
Decision: docs/decisions/012-rationale-session-guidance.md

## Goal

Let a caller optionally inject a standing system-prompt string into the
spawned headless session, without `session.py` knowing anything about
rationale or the miner.

## Acceptance criteria

- `SessionRunner.__init__` gains a `system_prompt: str = ""` parameter.
- When non-empty, the constructed child command includes
  `--append-system-prompt <system_prompt>`.
- When empty (default), the command is unchanged from today — existing
  `SessionRunner` tests keep passing with no `system_prompt` argument.
- A new test asserts the flag is present/absent in the built command for
  both cases, using the existing stub-script test double (no real `claude`
  binary invoked).

## Likely files

- `graphwerk/session.py` — `SessionRunner.__init__` and command-building.
- `tests/test_session.py` (or equivalent) — new constructor cases.

## Out of scope

- Deciding what string gets passed in (ticket 041) or wiring it from
  `cli._serve` (ticket 043).
- Any CLI flag to customize/disable guidance (ADR 012, Out of scope).
