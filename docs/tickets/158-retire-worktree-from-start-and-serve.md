# 158. Retire the worktree from `start`/`serve`

Status: ready
Decision: docs/decisions/058-retire-worktree-single-directory-review.md

## Goal

`graphwerk start`/`serve` operate on one repository directory plus an
optional base ref — no shadow worktree is created. `ShadowWorkspace` and
its `git worktree add`/`remove` calls are deleted.

## Acceptance criteria

- `serve` takes `--repo PATH` (default `.`) and an optional `--base-ref`
  (default: current `HEAD`) instead of `--base`/`--staged`.
- `start` no longer takes `--staging`/`--branch` and no longer creates a
  worktree; it prints the `claude` invocation to run in the repo directory
  itself (or launches it there) and serves the UI against that one
  directory.
- `graphwerk/staging/workspace.py` (`ShadowWorkspace`) is deleted; no
  remaining caller references it.
- Running `serve`/`start` against a repo with uncommitted local changes at
  session start does not error — those changes are simply part of the
  initial diff against the base ref.

## Likely files

- `graphwerk/cli.py` — argument parsing and `_serve`/`start` wiring.
- `graphwerk/staging/workspace.py` — delete.
- `graphwerk/bootstrap.py` — `build_app()` signature (one repo path + base
  ref instead of base/staged paths).

## Out of scope

- `graphwerk demo`'s two-tree setup (ticket 162).
- The mutation-engine endpoints this makes unreachable (ticket 159).
