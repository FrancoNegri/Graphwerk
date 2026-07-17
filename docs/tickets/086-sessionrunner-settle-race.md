# 086. `SessionRunner._settle` is not safe under concurrent status polls

Status: ready
Decision: docs/audit/runs/001-2026-07-17.md

## Goal

`SessionRunner.status()` can be called concurrently (FastAPI serves the
sync `/api/session` and `/api/prompt` endpoints from a threadpool, and the
documented setup has more than one client polling — a LAN device plus a
local tab) without ever double-entering `_settle()`. Today two threads can
both observe `poll()` returning an exit code before either clears
`self._child`; the second then crashes on `self._child_output.seek(0)`
after the first closed it and set it to `None` — a 500 on `/api/session`
at the exact moment a session finishes, and potentially inconsistent
runner state.

## Acceptance criteria

- A regression test drives `status()` from two threads across the child's
  exit (e.g. a stub child whose `poll()` flips to an exit code once, or a
  barrier that forces both threads past the `poll()` check before either
  settles) and asserts no exception is raised and the final state is a
  single consistent `done`/`failed`.
- `_settle()` runs at most once per child process regardless of how many
  concurrent `status()` calls observe the exit (e.g. a `threading.Lock`
  around the poll-and-settle section, or an equivalent idempotence guard).
- `start()`'s busy check participates in the same protection, so a
  `start()` racing a settling poll can't observe a half-settled state.
- Existing `tests/test_session.py` behavior is unchanged (stub script
  pattern, no real `claude` binary).

## Likely files

- `graphwerk/session.py` — lock/guard around poll-and-settle.
- `tests/test_session.py` — concurrency regression test.

## Out of scope

- Any change to the endpoint layer or polling cadence.
- Multi-session support (roadmap Phase 5).
