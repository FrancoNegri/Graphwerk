"""Enumerates candidate git refs for the comparison picker (ADR 060): every
local branch, every tag, and the most recent N commits on the current
branch. Same permissive posture as the git-plumbing helpers in
`staging/differ.py` — a repo with no commits yet, or a `repo_root` that
isn't a git repository at all, yields an empty list rather than raising.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

RECENT_COMMIT_LIMIT = 20


def list_refs(repo_root: Path, recent_commit_limit: int = RECENT_COMMIT_LIMIT) -> list[dict]:
    """Branches, then tags, then the most recent `recent_commit_limit`
    commits on the current branch. Each entry has `ref` (what to pass back
    as a `base`/`staged` query param), `label` (what to show the user), and
    `kind` (`branch`/`tag`/`commit`)."""
    refs: list[dict] = []
    for name in _git_lines(repo_root, ["for-each-ref", "--format=%(refname:short)", "refs/heads"]):
        refs.append({"ref": name, "label": name, "kind": "branch"})
    for name in _git_lines(repo_root, ["for-each-ref", "--format=%(refname:short)", "refs/tags"]):
        refs.append({"ref": name, "label": name, "kind": "tag"})
    for line in _git_lines(repo_root, ["log", "--oneline", "-n", str(recent_commit_limit)]):
        sha, _, message = line.partition(" ")
        refs.append({"ref": sha, "label": line, "kind": "commit"})
    return refs


def _git_lines(repo_root: Path, args: list[str]) -> list[str]:
    """Non-empty stdout lines from `git -C repo_root <args>`, or an empty
    list when the command fails — not a git repository, or (for `log`) no
    commits yet."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    return [line for line in result.stdout.splitlines() if line]
