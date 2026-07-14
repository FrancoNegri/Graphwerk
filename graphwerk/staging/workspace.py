"""Shadow workspace management.

The agent works in a real, isolated copy of the repo (a git worktree), so its
read-back/build/test loop stays intact. The differ only compares two directory
trees, so any directory pair works — the worktree is just the recommended way
to produce one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class ShadowWorkspace:
    def __init__(self, repo_root: Path, staging_root: Path):
        self.repo_root = repo_root
        self.staging_root = staging_root

    @classmethod
    def ensure(
        cls,
        repo_root: Path,
        staging_root: Path,
        branch: str = "graphwerk-staging",
    ) -> "ShadowWorkspace":
        """Create the staging worktree if it doesn't exist yet."""
        if not staging_root.exists():
            _git(repo_root, "worktree", "add", "-B", branch, str(staging_root))
        return cls(repo_root, staging_root)

    def remove(self) -> None:
        _git(self.repo_root, "worktree", "remove", "--force", str(self.staging_root))


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
