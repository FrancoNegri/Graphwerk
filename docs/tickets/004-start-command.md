# 004. `graphwerk start` command

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md

Depends on: tickets 001, 002.

## Goal

One command takes a repo from zero to reviewable: worktree ensured, `claude`
invocation printed, UI served.

## Acceptance criteria

- `python -m graphwerk start [--repo PATH] [--staging PATH] [--branch NAME]
  [--host] [--port]`; `--repo` defaults to the cwd, `--staging` defaults to
  a sibling directory `<repo-name>-graphwerk-staging`, `--branch` to
  `graphwerk-staging`.
- Ensures the worktree via the existing `ShadowWorkspace.ensure` (creates
  when absent, reuses when present).
- Prints the invocation to run the agent in the worktree
  (`cd <staging> && claude`) before serving.
- Serves with base = repo, staged = worktree, transcript auto-discovered
  (no `--transcript` flag on `start`).
- Errors clearly (nonzero exit, message) when `--repo` is not a git repo.
- Argument handling is unit-tested; serving reuses the existing `_serve`
  path.

## Likely files

- `graphwerk/cli.py` — new subcommand + default-staging-path helper
- `tests/test_cli.py` (or equivalent) — new cases

## Out of scope

Launching or driving the `claude` process (Phase 3). Worktree cleanup
(`ShadowWorkspace.remove` exists; a `stop` command can come later if
dogfooding wants it).
