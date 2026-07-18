# 106. `SessionRunner.resume(prompt)` re-enters the stored session

Status: done
Decision: docs/decisions/040-post-session-check-gate.md

## Goal

`SessionRunner` can send a follow-up prompt into the session it last
completed — the `--resume` machinery its stored `_last_session_id` was
groundwork for (ADR 011).

## Acceptance criteria

- `resume(prompt)` spawns
  `claude -p <prompt> --resume <last_session_id>` with the same
  output-format, permission-mode, and `--append-system-prompt` flags,
  output capture, and settle behavior as `start`.
- Raises `SessionBusyError` while a child is running; raises a clear
  error when no session id is stored (nothing to resume).
- A successful resumed run updates the stored session id from the result
  (same parse as `start`); state transitions (`running`/`done`/`failed`)
  are identical to `start`'s.
- Tests use the existing stub-script pattern, asserting the `--resume`
  argument and id handling; no real binary.

## Likely files

- `graphwerk/session.py` — extract the shared spawn path from `start`;
  add `resume`.
- `tests/test_session.py` — new cases.

## Out of scope

- Who calls `resume` and with what prompt (ticket 107).
- The Phase 3 reject flow (reuses this later).
