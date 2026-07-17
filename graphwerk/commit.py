"""Commit the whole staged change set into the base repo (ADR 037).

Every changed file is applied file-level via the existing ApplyEngine, then
`git add` scoped to exactly those paths keeps a dirty base tree's unrelated
files out of the reviewer's commit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from graphwerk.apply import ApplyEngine
from graphwerk.models import Status
from graphwerk.staging import ChangeSetBuilder

CHANGED_STATUSES = {Status.MODIFIED, Status.ADDED, Status.DELETED}


class CommitError(ValueError):
    """A preflight or git failure the reviewer can act on."""


class CommitEngine:
    def __init__(self, base_root: Path, apply_engine: ApplyEngine,
                 change_set_builder: ChangeSetBuilder):
        self.base_root = base_root
        self.apply_engine = apply_engine
        self.change_set_builder = change_set_builder

    def commit_all(self, message: str) -> dict:
        if not message.strip():
            raise CommitError("commit message is required")
        if not self._base_is_git_repo():
            raise CommitError(
                f"{self.base_root} is not a git repository — committing needs one "
                f"(the scripted demo trees are plain directories)"
            )
        changed_paths = sorted(
            rel for rel, change in self.change_set_builder.build().items()
            if change.status in CHANGED_STATUSES
        )
        if not changed_paths:
            raise CommitError("nothing to commit — the change set is empty")
        for rel_path in changed_paths:
            self.apply_engine.apply_file(rel_path)
        self._git("add", "--", *changed_paths)
        self._git("commit", "-m", message)
        short_hash = self._git("rev-parse", "--short", "HEAD").stdout.strip()
        return {"paths": changed_paths, "commit": short_hash}

    def _base_is_git_repo(self) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.base_root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", "-C", str(self.base_root), *args],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise CommitError(f"git {args[0]} failed: {result.stderr.strip()}")
        return result
