# 108. `--check`/`--check-retries` flags; `/api/session` reports the cycle

Status: done
Decision: docs/decisions/040-post-session-check-gate.md

## Goal

The check gate is configurable from the command line and observable from
the API: `serve`/`start` accept the check command, and `/api/session`
reports the cycle's state instead of the bare runner's.

## Acceptance criteria

- `serve` and `start` accept `--check "<command>"` (default: none — gate
  off, behavior unchanged) and `--check-retries N` (default 1), threaded
  into a `SessionCycle` wrapping the existing `SessionRunner`.
- `/api/session` returns the cycle's status payload: state (including
  `checking` / `resuming` / `check_failed`), attempt count, and last
  check exit code + output tail; `POST /api/prompt` still 409s for the
  whole cycle, not just while the agent subprocess runs.
- With no `--check`, the endpoint payload is backward-compatible with
  today's shape (state/detail/session_id).
- Server tests cover: gate off (unchanged shape), gate on with a passing
  stub check, gate on with a failing stub check surfacing
  `check_failed` + tail.

## Likely files

- `graphwerk/cli.py` — the two flags, `SessionCycle` construction in
  `_serve`.
- `graphwerk/server.py` — `/api/session` and `/api/prompt` talk to the
  cycle.
- `tests/test_server.py` — new cases.

## Out of scope

- UI rendering of the new states (ticket 109).
- A config file for check settings (ADR 040 deferral).
