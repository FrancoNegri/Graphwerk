# 132. Wire the scope guard into spawned sessions

Status: done
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

A session started with a `scope` actually gets its write access restricted
— `SessionRunner`/`SessionCycle` configure the Claude Code PreToolUse hook
(ticket 131) into the staged worktree before spawning, so "design can't
touch code, implementation can't touch docs" is enforced, not just
requested via prompt text.

## Acceptance criteria

- `SessionRunner.start(prompt, scope=None)` and `.resume(prompt,
  scope=None)` (`graphwerk/session.py`): when `scope` is `"design"` or
  `"implementation"`, write the Claude Code hook configuration (settings
  file entry pointing at `scope_guard.py` with the scope, per whatever
  mechanism Claude Code's PreToolUse hooks require) into the staged
  worktree before spawning `claude -p`; when `scope` is `None`, no hook
  config is written — today's unrestricted behavior, unchanged.
- `SessionCycle.start`/`continue_session` (`graphwerk/cycle.py`) accept and
  forward the same `scope` parameter.
- `PromptRequest`/`/api/prompt` (`graphwerk/server.py`) accept the
  `scope` field from the frontend (ticket 130) and pass it through.
- A denied `Edit`/`Write` surfaces to the agent as a normal permission
  refusal (verify via an integration test: a design-scoped session asked
  to edit a `.py` file gets denied, and the denial doesn't corrupt the
  session's `--output-format json` result parsing).

## Likely files

- `graphwerk/session.py` — hook config writing, `scope` parameter.
- `graphwerk/cycle.py` — `scope` threading.
- `graphwerk/server.py` — `PromptRequest.scope`.
- `tests/test_session.py`, `tests/test_cycle.py`, `tests/test_server.py` —
  scope threading and hook-config-written cases.

## Out of scope

- `scope_guard.py`'s decision logic itself (ticket 131, already done).
- The frontend toggle that produces the `scope` value (ticket 130, already
  done).
