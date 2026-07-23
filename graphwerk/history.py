"""Mines git *history* (not just two ref snapshots) for ticket -> commit ->
file linkage (ADR 065): every landed ticket's own commit already starts
"Ticket NNN: ..." (this repo's own convention, visible in plain `git log`
today), so a ticket's real blast radius is ground truth from that history,
not a ticket's own "Likely files" prose written before implementation. Same
permissive posture as `graphwerk/refs.py`: a repo with no matching commits,
or no git repository at all, yields empty results rather than raising.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def commits_for_ticket(repo_root: Path, ticket_number: int) -> list[str]:
    """Every commit sha whose message starts "Ticket <ticket_number>: ...",
    searched across all refs (not just the current branch) since a landed
    ticket's commit may live on a branch merged in elsewhere. The `^` anchor
    plus the trailing colon keeps "Ticket 1:" from also matching "Ticket
    12:"."""
    return _git_lines(
        repo_root,
        ["log", "--all", "--format=%H", f"--grep=^Ticket {ticket_number}:"],
    )


def changed_files_for_commits(repo_root: Path, shas: list[str]) -> set[str]:
    """Union of every file each commit's own diff-tree touched. `git
    diff-tree --name-only` already emits paths relative to the repo root,
    same convention `FileIndex.rel_path` uses, so no further normalization
    is needed."""
    changed: set[str] = set()
    for sha in shas:
        # --root: a ticket's first-ever commit in a fresh repo has no
        # parent, and diff-tree shows nothing for a parentless commit
        # without it (diffs against the empty tree instead of showing
        # nothing).
        changed.update(
            _git_lines(repo_root, ["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha])
        )
    return changed


def _git_lines(repo_root: Path, args: list[str]) -> list[str]:
    """Non-empty stdout lines from `git -C repo_root <args>`, or an empty
    list when the command fails — not a git repository, an unresolvable
    sha, or (for `log`) no matching commits. Kept as its own private
    helper rather than shared with `refs.py`'s identical-looking one: each
    git-facing module here stays self-contained (differ.py and refs.py
    each already keep their own private git helper too)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    return [line for line in result.stdout.splitlines() if line]
