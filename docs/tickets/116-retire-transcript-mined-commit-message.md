# 116. Retire the transcript-mined commit message; clear on commit/discard

Status: ready
Decision: docs/decisions/042-regenerated-commit-message-per-cycle.md

## Goal

Remove ADR 037's superseded mining mechanism (tickets 095/096) now that
ADR 042's regenerated message is the source of truth, and reset the held
message once a review cycle actually ends (commit or discard succeeds).

## Acceptance criteria

- `SESSION_GUIDANCE` no longer instructs the agent to close with a
  `Commit-message:` line.
- `parse_commit_message` and its regex (`graphwerk/rationale/
  attribution.py`) are deleted, along with the round-trip test(s) written
  for ticket 095.
- `RationaleStore.commit_message` and the `reload()` call that populates
  it are deleted; `GraphService.snapshot()` no longer sets
  `meta["commit_message"]` (superseded by `SessionCycle.status()`'s
  `commit_message`, wired in ticket 115).
- `SessionCycle` gains a way to clear the held message (e.g.
  `clear_commit_message()` or folded into an existing reset path); the
  `/api/commit` and `/api/discard` route handlers call it after a
  successful commit/discard, so the next review cycle starts with an
  empty box rather than the previous cycle's leftover message.
- Existing tests referencing `meta.commit_message` / `parse_commit_message`
  / the guidance line are updated or removed accordingly; the rest of the
  rationale/service test suites stay green.

## Likely files

- `graphwerk/rationale/guidance.py`, `graphwerk/rationale/attribution.py`,
  `graphwerk/rationale/miner.py` — remove the mining path
- `graphwerk/service.py` — drop the `meta["commit_message"]` assignment
- `graphwerk/cycle.py` — add the clear method
- `graphwerk/server.py` — call it from `/api/commit`/`/api/discard`
- `tests/rationale/`, `tests/test_service.py`, `tests/test_cycle.py`,
  `tests/test_server.py` — updates

## Out of scope

The regeneration mechanism itself (tickets 113-115). Frontend (117).
