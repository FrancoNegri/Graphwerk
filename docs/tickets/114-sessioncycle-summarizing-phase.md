# 114. `SessionCycle` gains a `summarizing` phase

Status: ready
Decision: docs/decisions/042-regenerated-commit-message-per-cycle.md

## Goal

After the check gate settles (pass or fail), `SessionCycle` spawns a
`CommitMessageRunner` over the current diff and holds in a transient
`summarizing` state until it settles, before reporting the existing
`done`/`check_failed` terminal states — carrying the generated message in
`status()` from then on.

## Acceptance criteria

- `SessionCycle` accepts a `commit_message_runner_factory` (a callable
  taking the current diff text and returning a fresh `CommitMessageRunner`,
  so the cycle doesn't need to import diff-building logic) and a
  `diff_provider` callable (returns the current diff text on demand).
- When `_advance_check_locked` would today set `self._state` to `"done"`
  or `"check_failed"`, it instead spawns the commit-message runner via the
  factory and sets `self._state = "summarizing"`.
- A new `_advance_summarizing_locked` polls the runner; while `running` it
  no-ops (same one-poll-per-status-call discipline as the existing
  advance methods). Once settled, it stores `self._commit_message` (on
  success) or leaves the previously-held value untouched (on failure),
  then transitions to whichever of `done`/`check_failed` was pending.
- `status()`'s payload gains `commit_message` (`None` until the first
  successful regeneration ever completes).
- `TERMINAL_STATES` is unchanged (`summarizing` is transient like
  `checking`/`resuming` — never returned as terminal).
- A second `start()` call does not clear `self._commit_message` — it stays
  at its last value throughout the new `running`/`checking`/`summarizing`
  chain and is only overwritten when *this* cycle's own summarizing step
  succeeds.
- Tests (fakes for runner/check-runner/commit-message-runner, mirroring
  `tests/test_cycle.py`'s existing style) cover: happy path reaches `done`
  with a message; check failure reaches `check_failed` with a message;
  commit-message-runner failure still reaches `done`/`check_failed` with
  the prior message (or `None` on a first-ever failure) instead of
  getting stuck; a second `start()` leaves the held message visible until
  the new cycle's own summarize step completes.

## Likely files

- `graphwerk/cycle.py` — state machine
- `tests/test_cycle.py` — coverage

## Out of scope

`CommitMessageRunner` itself (ticket 113). Server wiring / what
`diff_provider` actually calls (ticket 115). Frontend (ticket 117).
