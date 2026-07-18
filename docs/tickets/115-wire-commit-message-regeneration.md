# 115. Wire diff-based regeneration into the running server

Status: ready
Decision: docs/decisions/042-regenerated-commit-message-per-cycle.md

## Goal

`cli.py`/`server.py` compose the new `commit_message_runner_factory` and
`diff_provider` into the `SessionCycle` they build, using the same change
set the rest of the app already diffs — no new diffing logic.

## Acceptance criteria

- A small function (e.g. in `graphwerk/commit_message.py`) turns a
  `ChangeSetBuilder`'s output into the single diff-text blob fed to
  `CommitMessageRunner` — concatenating each changed file's existing
  `.diff`, skipping unchanged files, in a form fit to drop into a prompt.
- The `diff_provider` passed into `SessionCycle` calls
  `service.builder.build()` (the same builder `GraphService.snapshot()`
  already uses) through that function — reusing the existing change-set
  computation rather than re-diffing.
- The `commit_message_runner_factory` closes over the configured
  `claude_cmd`/model default, matching how `SessionRunner`'s `claude_cmd`
  is already threaded through `cli.py`.
- `/api/session`'s existing pass-through of `runner.status()` now includes
  `commit_message` for free (no route change needed beyond what ticket
  114 already put in the dict).
- Test (server or cli integration level, whichever existing suite fits)
  confirms a full `/api/prompt` → poll `/api/session` cycle against a fake
  `claude` stub ends with `commit_message` populated from the diff text
  the fake was given.

## Likely files

- `graphwerk/commit_message.py` — diff-text builder function
- `graphwerk/cli.py` (or `server.py`, wherever `SessionCycle` is
  constructed today) — wiring
- `tests/test_cli.py` / `tests/test_server.py` — coverage

## Out of scope

Clearing `commit_message` on commit/discard (ticket 116). Removing the
old mining path (ticket 116). Frontend (ticket 117).
