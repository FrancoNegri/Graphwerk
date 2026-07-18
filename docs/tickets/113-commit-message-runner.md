# 113. `CommitMessageRunner`: one-shot diff-summarizing `claude -p` call

Status: ready
Decision: docs/decisions/042-regenerated-commit-message-per-cycle.md

## Goal

A small class that, given the current diff text, spawns one headless
`claude -p` call asking for a single-line conventional-commit summary of
the whole change set, and can be polled to completion — same shape as
`SessionRunner`/`CheckRunner`, but stateless (no `--resume`, no file-edit
permissions).

## Acceptance criteria

- `CommitMessageRunner(diff_text, claude_cmd="claude", model="haiku")` (or
  equivalent constructor) exposes `start()` and `status()`; `status()`
  returns `{"state": "running" | "done" | "failed", "message": str | None,
  "detail": str}`.
- `start()` builds a prompt asking for exactly one line summarizing the
  given diff text and spawns `claude -p <prompt> --model <model>
  --output-format json`, mirroring `SessionRunner._spawn`'s subprocess
  handling (separate stdout/stderr temp files, non-blocking poll).
- On success, `status()` extracts the assistant's one-line text response
  as `message` (trimmed; `None` if the response is empty after trimming).
- On a non-zero exit or unparseable output, `state` is `"failed"` with a
  `detail` describing why — mirroring `SessionRunner._settle`'s failure
  handling — and `message` stays `None`.
- Tests fake the `claude_cmd` subprocess (a stub script, same technique as
  `tests/test_session.py`) covering: happy path (one-line message
  returned), non-zero exit, unparseable output.

## Likely files

- `graphwerk/commit_message.py` — new class
- `tests/test_commit_message.py` — coverage

## Out of scope

Wiring into `SessionCycle` (ticket 114). Choosing what diff text to feed
it or when to call it (ticket 114/115). No tool/file-edit permissions are
requested by this call at all — it's a read-only text response.
