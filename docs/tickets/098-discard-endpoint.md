# 098. Discard-all: engine + `/api/discard`

Status: done
Decision: docs/decisions/037-bottom-session-bar-commit-discard.md

## Goal

One POST returns the staging tree to zero by reverse-applying the current
change set: added files deleted, modified and deleted files restored from
base.

## Acceptance criteria

- A small engine class (e.g. `DiscardEngine`) that enumerates the change
  set (via `ChangeSetBuilder`) and, per changed file: deletes it from the
  staging tree if `added`, copies the base version over it if `modified`
  or `deleted`. Unchanged files and everything outside the change set
  (agent scratch, settings) are untouched.
- Path-escape protection equivalent to `ApplyEngine.apply_file`'s
  `_is_within` checks.
- `POST /api/discard` refuses with HTTP 409 while the session runner
  reports `running`; otherwise returns the list of reverted paths.
- After a discard, a fresh snapshot reports no changed nodes (tested
  end-to-end against temp trees).
- Tests cover: added/modified/deleted round-trip to a clean diff, refusal
  while a fake runner reports running, non-change-set files untouched.

## Likely files

- `graphwerk/apply.py` (or sibling module) — engine
- `graphwerk/server.py` — endpoint, wired to the session runner's status
- `tests/` — engine + endpoint coverage

## Out of scope

Non-Python staged files (ticket 009's differ gap — same limitation,
documented in the ADR). UI wiring (099). Clearing the mined commit
message client-side (099).
