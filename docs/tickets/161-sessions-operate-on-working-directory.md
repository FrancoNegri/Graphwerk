# 161. Sessions and checks operate on the working directory, not a worktree path

Status: done
Decision: docs/decisions/058-retire-worktree-single-directory-review.md

## Goal

`SessionRunner`, `SessionCycle`, and `CheckRunner` spawn, resume, and run
the configured check command in the developer's single repo directory
instead of a shadow-worktree path. Behavior (spawn, resume, bounded
auto-retry on check failure, design-mode dialogue) is otherwise unchanged.

## Acceptance criteria

- `bootstrap.build_app()` constructs `SessionRunner`/`SessionCycle` with
  the one repo directory (from ticket 158) instead of a `staged` path.
- A prompt sent via `/api/prompt` spawns Claude in that directory; a
  configured check command runs there too.
- Resuming a session (`continue_session`) operates in the same directory.
- Existing `SessionRunner`/`SessionCycle`/`CheckRunner` tests pass with a
  single directory fixture in place of a base/staged pair.

## Likely files

- `graphwerk/bootstrap.py` — pass the one repo directory to
  `SessionRunner`/`SessionCycle`/`CheckRunner` construction.
- `graphwerk/session.py`, `graphwerk/cycle.py`, `graphwerk/check.py` —
  confirm/adjust any parameter naming that still implies a "staged" path
  distinct from "the repo."

## Out of scope

- Any change to session spawning mechanics (permission modes, resume
  semantics, retry bounds) beyond the directory they operate in.
