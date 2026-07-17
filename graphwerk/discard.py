"""Return the staging tree to zero by reverse-applying the change set (ADR 037).

Added files are deleted, modified and deleted files are restored from base.
Everything outside the change set — agent scratch, settings, non-Python
files — is untouched, so the discard removes exactly what the graph showed.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from graphwerk.apply import is_within
from graphwerk.models import Status
from graphwerk.staging import ChangeSetBuilder

CHANGED_STATUSES = {Status.MODIFIED, Status.ADDED, Status.DELETED}


class DiscardEngine:
    def __init__(self, base_root: Path, staged_root: Path,
                 change_set_builder: ChangeSetBuilder):
        self.base_root = base_root
        self.staged_root = staged_root
        self.change_set_builder = change_set_builder

    def discard_all(self) -> list[str]:
        reverted: list[str] = []
        for rel_path, change in self.change_set_builder.build().items():
            if change.status not in CHANGED_STATUSES:
                continue
            self._revert_file(rel_path, change.status)
            reverted.append(rel_path)
        return sorted(reverted)

    def _revert_file(self, rel_path: str, status: Status) -> None:
        base_path = self.base_root / rel_path
        staged_path = self.staged_root / rel_path
        if not is_within(self.base_root, base_path) or not is_within(self.staged_root, staged_path):
            raise ValueError(f"path escapes workspace: {rel_path}")
        if status is Status.ADDED:
            staged_path.unlink()
            return
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(base_path, staged_path)
