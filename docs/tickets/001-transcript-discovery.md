# 001. Transcript auto-discovery function

Status: done
Decision: docs/decisions/001-phase-2-real-session.md

## Goal

Given a worktree path, find the Claude Code session transcript for it —
no more digging through `~/.claude/projects/` by hand.

## Acceptance criteria

- `find_latest_transcript(worktree: Path, claude_dir: Path = ~/.claude) -> Path | None`
  in a new `graphwerk/rationale/discovery.py`.
- The worktree path is encoded to its project directory name by replacing
  `/` and `.` with `-` (e.g. `/home/u/my.repo` → `-home-u-my-repo`); the
  encoding lives in its own small function so a Claude Code format change is
  a one-line fix.
- Returns the most recently modified `*.jsonl` in
  `<claude_dir>/projects/<encoded>/`.
- Returns `None` when the project directory doesn't exist or holds no
  `.jsonl` files.
- Tests use a tmp `claude_dir`; nothing touches the real `~/.claude`.

## Likely files

- `graphwerk/rationale/discovery.py` — new module
- `tests/test_discovery.py` — new tests

## Out of scope

Wiring into `RationaleStore` or the CLI (ticket 002). Watching or merging
multiple sessions (Phase 5).
