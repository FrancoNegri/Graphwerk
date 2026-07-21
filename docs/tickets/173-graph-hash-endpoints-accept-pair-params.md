# 173. `/api/graph` and `/api/hash` accept `base`/`staged` query params

Status: done
Decision: docs/decisions/060-comparison-picker-any-ref-vs-any-ref.md

## Goal

Depends on ticket 171 (the registry). Wire the registry into the running
server so a caller can request any `(base, staged)` pair via query params,
while omitting both preserves today's exact behavior (the CLI's configured
base ref vs. the working directory) for backward compatibility with the
current frontend and any existing bookmarked/scripted usage.

## Acceptance criteria

- `graphwerk/server.py`'s `create_app` takes the registry (or a factory
  wired in `bootstrap.py`) instead of / alongside a single `service:
  GraphService`.
- `GET /api/graph?base=<ref>&staged=<ref>` resolves both through the
  registry and returns that pair's snapshot; omitting either or both
  params falls back to the CLI-configured default pair (today's `base_ref`
  and the working-directory token), so `GET /api/graph` with no params is
  byte-for-byte the same response shape as before this ticket.
- `GET /api/hash?base=<ref>&staged=<ref>` mirrors the same param handling
  against the resolved pair's `GraphService.state_hash()`.
- A test hits `/api/graph` with no params and confirms it matches today's
  default-pair behavior; a second test hits it with an explicit historical
  `(base, staged)` pair (both real commits in a temp repo) and confirms the
  returned snapshot reflects that pair's diff, not the default one.

## Likely files

- `graphwerk/server.py` — route param handling.
- `graphwerk/bootstrap.py` — wiring the registry in instead of a single service.
- `tests/test_server.py` — param-handling tests.

## Out of scope

- The frontend dropdown itself (ticket 174) and gating the prompt
  box/polling on the resolved pair (ticket 175).
- Changing `/api/prompt` or `/api/session` — those stay tied to the one
  live `SessionCycle` regardless of which pair `/api/graph` is serving,
  per ADR 060.
