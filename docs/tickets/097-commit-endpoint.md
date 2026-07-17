# 097. Commit-all: engine + `/api/commit`

Status: ready
Decision: docs/decisions/037-bottom-session-bar-commit-discard.md

## Goal

One POST commits the whole staged change set into the base repo: every
changed file is applied file-level, then committed with the caller's
message.

## Acceptance criteria

- A small engine class (e.g. `CommitEngine`) that, given the change set:
  applies every `modified`/`added`/`deleted` file to base via the existing
  `ApplyEngine.apply_file`, then runs `git add -- <those paths>` and
  `git commit -m <message>` in the base root via stdlib `subprocess`.
- Preflight, before any file is touched: the base root is inside a git
  repository (else a clear error naming the demo-tree case), the message
  is non-empty, the change set is non-empty.
- Only the applied paths are staged into the commit — a pre-existing dirty
  file elsewhere in the base tree is not swept in (tested).
- `POST /api/commit` with `{message}` returns the applied paths and the
  new commit's short hash; preflight failures map to HTTP 400.
- Tests use temporary git repos (`git init` fixtures) covering: happy
  path, deleted file, dirty unrelated file excluded, non-git base
  rejected before any apply.

## Likely files

- `graphwerk/apply.py` (or a sibling `commit.py`) — engine
- `graphwerk/server.py` — endpoint + request model
- `tests/test_server.py` + an engine test module — coverage

## Out of scope

Commit message generation (095/096) and UI (099). Discard (098). Branch
strategy, push, partial/subset commits.
