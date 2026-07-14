# 002. RationaleStore uses auto-discovered transcripts

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md

Depends on: ticket 001.

## Goal

`graphwerk serve` without `--transcript` mines the "why" from the latest
Claude session for the staged worktree, automatically — including sessions
started after the server.

## Acceptance criteria

- When `RationaleStore` is constructed with a `staged_root` but no
  `transcript_path`, each `reload()` re-resolves the transcript via
  `find_latest_transcript(staged_root)` before mining; a session created
  after construction is picked up, and a newer session wins.
- An explicit `transcript_path` stays pinned — discovery never overrides it.
- Discovery finding nothing behaves exactly like today's no-transcript case
  (sidecar-only rationale, no errors).
- Existing miner tests keep passing unchanged.

## Likely files

- `graphwerk/rationale/miner.py` — resolve-on-reload logic
- `tests/test_rationale.py` (or equivalent) — new cases

## Out of scope

CLI changes (`serve` already passes `staged_root`; `start` is ticket 004).
