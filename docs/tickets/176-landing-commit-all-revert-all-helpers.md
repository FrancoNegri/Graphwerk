# 176. `graphwerk/landing.py`: `commit_all` / `revert_all` git helpers

Status: done
Decision: docs/decisions/061-whole-tree-commit-all-revert-all.md

## Goal

Provide the two pure git-subprocess functions ADR 061 needs, independently
testable against a temp git repo, with no server/service wiring yet.

## Acceptance criteria

- `commit_all(repo_root: Path, paths: list[str], message: str) -> None` in
  new `graphwerk/landing.py` runs `git add -- <paths>` then `git commit -m
  <message>` in `repo_root` (subprocess, same invocation style as
  `_git_ls_tree`/`_git_show_bytes` in `graphwerk/staging/differ.py`) — but
  unlike those read helpers, a failure must raise rather than be
  swallowed, since a failed commit needs to surface to the caller.
- `revert_all(repo_root: Path, paths: list[str]) -> None` runs `git stash
  push -u -- <paths>` in `repo_root`, same raise-on-failure posture.
- Empty `paths` is a no-op for both — never invoke `git` with no pathspec
  (which would silently operate on the whole tree instead of nothing).
- A test builds a temp git repo, modifies/adds/deletes a few files, calls
  `commit_all` with a subset of paths and a message, and asserts `git log
  -1 --format=%s` matches the message and `git status --porcelain` still
  reports only the untouched files as dirty (the rest got committed).
- A second test calls `revert_all` with a subset of paths, asserts those
  paths are restored to `HEAD`'s content, `git stash list` has exactly one
  entry, and untouched files are unaffected.

## Likely files

- `graphwerk/landing.py` (new) — the two functions.
- `tests/test_landing.py` (new) — the tests above.

## Out of scope

- Deciding which paths count as "changed" — that's ticket 177
  (`GraphService.changed_paths()`).
- Any server/route wiring — ticket 178.
- Any UI — ticket 179.
