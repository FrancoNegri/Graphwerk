"""Locate the Claude Code session transcript for a worktree.

Claude Code stores transcripts under ``~/.claude/projects/<encoded path>/``.
The encoding convention is undocumented, so it is isolated in
``project_dir_name`` — if the format changes, the fix is one line.
"""

from __future__ import annotations

from pathlib import Path


def project_dir_name(worktree: Path) -> str:
    return str(worktree).replace("/", "-").replace(".", "-")


def find_latest_transcript(worktree: Path, claude_dir: Path = Path.home() / ".claude") -> Path | None:
    project_dir = claude_dir / "projects" / project_dir_name(worktree)
    transcripts = project_dir.glob("*.jsonl")
    return max(transcripts, key=lambda transcript: transcript.stat().st_mtime, default=None)
