"""Symbol-level diff between the base tree and the staged (shadow) tree.

Rather than mapping textual hunks onto symbols, both versions of each file are
parsed and symbols are compared by qualified name — sidestepping hunk/symbol
alignment entirely (docs/03-architecture-notes.md, hard problem #1).
"""

from __future__ import annotations

import difflib
from pathlib import Path

from graphwerk.indexing.python_ast import index_tree
from graphwerk.models import FileIndex, Status


class FileChange:
    def __init__(
        self,
        rel_path: str,
        status: Status,
        base: FileIndex | None,
        staged: FileIndex | None,
        diff: str,
    ):
        self.rel_path = rel_path
        self.status = status
        self.base = base
        self.staged = staged
        self.diff = diff
        # qualname -> (status, symbol-level unified diff)
        self.symbols: dict[str, tuple[Status, str]] = {}


class ChangeSetBuilder:
    def __init__(self, base_root: Path, staged_root: Path):
        self.base_root = base_root
        self.staged_root = staged_root

    def build(self) -> dict[str, FileChange]:
        base_files = index_tree(self.base_root)
        staged_files = index_tree(self.staged_root)
        changes: dict[str, FileChange] = {}

        for rel in sorted(set(base_files) | set(staged_files)):
            base, staged = base_files.get(rel), staged_files.get(rel)
            if base is not None and staged is None:
                change = FileChange(rel, Status.DELETED, base, None, self._file_diff(rel))
                for qualname in base.symbols:
                    change.symbols[qualname] = (Status.DELETED, self._symbol_diff(base, None, qualname))
            elif base is None and staged is not None:
                change = FileChange(rel, Status.ADDED, None, staged, self._file_diff(rel))
                for qualname in staged.symbols:
                    change.symbols[qualname] = (Status.ADDED, self._symbol_diff(None, staged, qualname))
            elif self._same_content(rel):
                change = FileChange(rel, Status.UNCHANGED, base, staged, "")
                for qualname in staged.symbols:
                    change.symbols[qualname] = (Status.UNCHANGED, "")
            else:
                change = FileChange(rel, Status.MODIFIED, base, staged, self._file_diff(rel))
                for qualname in sorted(set(base.symbols) | set(staged.symbols)):
                    in_base, in_staged = qualname in base.symbols, qualname in staged.symbols
                    if in_base and not in_staged:
                        status = Status.DELETED
                    elif in_staged and not in_base:
                        status = Status.ADDED
                    elif base.symbols[qualname].source != staged.symbols[qualname].source:
                        status = Status.MODIFIED
                    else:
                        status = Status.UNCHANGED
                    diff = "" if status is Status.UNCHANGED else self._symbol_diff(base, staged, qualname)
                    change.symbols[qualname] = (status, diff)
            changes[rel] = change
        return changes

    def _same_content(self, rel: str) -> bool:
        try:
            return (self.base_root / rel).read_bytes() == (self.staged_root / rel).read_bytes()
        except OSError:
            return False

    def _file_diff(self, rel: str) -> str:
        base_lines = _read_lines(self.base_root / rel)
        staged_lines = _read_lines(self.staged_root / rel)
        return "".join(
            difflib.unified_diff(base_lines, staged_lines, fromfile=f"base/{rel}", tofile=f"staged/{rel}")
        )

    def _symbol_diff(self, base: FileIndex | None, staged: FileIndex | None, qualname: str) -> str:
        base_src = base.symbols[qualname].source if base and qualname in base.symbols else ""
        staged_src = staged.symbols[qualname].source if staged and qualname in staged.symbols else ""
        return "".join(
            difflib.unified_diff(
                base_src.splitlines(keepends=True),
                staged_src.splitlines(keepends=True),
                fromfile=f"base::{qualname}",
                tofile=f"staged::{qualname}",
            )
        )


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return []
