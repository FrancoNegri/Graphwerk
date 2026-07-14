# 003. Git-aware file enumeration (.gitignore + symlinks)

Status: done
Decision: docs/decisions/001-phase-2-real-session.md

## Goal

Real repos index cleanly: .gitignored/generated files and symlinks stop
leaking into the graph, while non-git directory pairs (the demo) keep
working exactly as before.

## Acceptance criteria

- When the root is inside a git work tree, `iter_python_files` enumerates
  via `git ls-files --cached --others --exclude-standard` filtered to `*.py`,
  so .gitignored files are excluded.
- Symlinked files and files under symlinked directories are skipped in both
  the git and fallback paths.
- A non-git root falls back to the current `rglob` walk with `IGNORED_DIRS`,
  byte-for-byte same results as today.
- Files listed by git but deleted on disk (unstaged deletions) don't crash
  indexing.
- Indexer, differ, and `GraphService.state_hash` all go through the one
  shared walk (they already call `iter_python_files`; keep it that way).

## Likely files

- `graphwerk/indexing/python_ast.py` — `iter_python_files` (or extract a
  small `graphwerk/indexing/walk.py` if it reads better)
- `tests/test_indexing.py` (or equivalent) — git and non-git cases (init a
  throwaway git repo in tmp for the git case)

## Out of scope

Performance tuning of the walk for very large repos; non-Python files.
