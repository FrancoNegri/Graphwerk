"""Tracks which staged files the reviewer has approved (ADR 050).

Server-lifetime, in-memory only, same idiom as SessionCycle (ADR 042) — no
persistence beyond the running process. Each approval is stamped with the
staged file's fingerprint so an edit after approval silently invalidates it,
without any other layer having to call back in to say so.
"""

from __future__ import annotations

from pathlib import Path

from graphwerk.indexing.walk import file_fingerprint

Fingerprint = tuple[int, int] | None


class ApprovalStore:
    def __init__(self, staged_root: Path):
        self.staged_root = staged_root
        self._fingerprints: dict[str, Fingerprint] = {}

    def approve(self, rel_path: str) -> None:
        self._fingerprints[rel_path] = self._current_fingerprint(rel_path)

    def is_approved(self, rel_path: str) -> bool:
        if rel_path not in self._fingerprints:
            return False
        return self._fingerprints[rel_path] == self._current_fingerprint(rel_path)

    def unapprove(self, rel_path: str) -> None:
        self._fingerprints.pop(rel_path, None)

    def approved_paths(self) -> set[str]:
        return {rel for rel in self._fingerprints if self.is_approved(rel)}

    def clear(self, paths) -> None:
        for rel_path in paths:
            self._fingerprints.pop(rel_path, None)

    def clear_all(self) -> None:
        self._fingerprints.clear()

    def _current_fingerprint(self, rel_path: str) -> Fingerprint:
        path = self.staged_root / rel_path
        return file_fingerprint(path) if path.exists() else None
