# 039. `/api/prompt` + `/api/session` endpoints and the permissions flag

Status: done
Decision: docs/decisions/011-prompt-box-session-kickoff.md

## Goal

The server exposes the SessionRunner: a prompt can be POSTed, session
status polled, and the spawned session's permission mode chosen at
graphwerk launch.

## Acceptance criteria

- `POST /api/prompt` with `{"prompt": "..."}` starts a run and returns
  its status; empty/missing prompt is a 400; a run already active is a
  409; a failed spawn surfaces the runner's message.
- `GET /api/session` returns the runner's status snapshot (state, exit
  detail, last session id).
- `serve` and `start` gain `--agent-permissions` (default `acceptEdits`),
  passed through to the runner; `demo` wires a runner too (a missing
  claude binary just reports `failed` — no special-casing).
- Existing endpoints and payloads unchanged.
- pytest via the FastAPI test client with a stubbed runner/binary:
  started, busy-409, bad-request, status round-trip.

## Likely files

- `graphwerk/server.py` — two endpoints
- `graphwerk/cli.py` — flag + runner construction
- `tests/` — endpoint coverage

## Out of scope

- Any UI (ticket 040).
- Auth/rate-limiting on the endpoints (ADR 011 records the LAN tradeoff).
