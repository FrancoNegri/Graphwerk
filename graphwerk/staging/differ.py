"""Symbol-level diff between the base tree and the staged (shadow) tree.

Rather than mapping textual hunks onto symbols, both versions of each file are
parsed and symbols are compared by qualified name — sidestepping hunk/symbol
alignment entirely (docs/03-architecture-notes.md, hard problem #1).
"""

from __future__ import annotations

import difflib
from pathlib import Path

from graphwerk.indexing.markdown import MarkdownExtractor
from graphwerk.indexing.python_ast import PythonAstExtractor
from graphwerk.indexing.walk import file_fingerprint, iter_markdown_files, iter_python_files
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
        # module name -> status
        self.imports: dict[str, Status] = {}
        # doc-link target rel_path -> status
        self.references: dict[str, Status] = {}
        # full staged text (base text for deleted files); None if unreadable
        self.source: str | None = None
        self.base_source: str | None = None
        self.staged_source: str | None = None


class ChangeSetBuilder:
    def __init__(self, base_root: Path, staged_root: Path):
        self.base_root = base_root
        self.staged_root = staged_root
        self._python_extractor = PythonAstExtractor()
        self._markdown_extractor = MarkdownExtractor()
        # (root, rel_path, mtime_ns, size) -> FileIndex; unbounded for the
        # process lifetime (ADR 019, out of scope: eviction/memory bounds).
        self._index_cache: dict[tuple[str, str, int, int], FileIndex] = {}

    def build(self) -> dict[str, FileChange]:
        base_files = self._index_tree(self.base_root)
        staged_files = self._index_tree(self.staged_root)
        changes: dict[str, FileChange] = {}

        for rel in sorted(set(base_files) | set(staged_files)):
            base, staged = base_files.get(rel), staged_files.get(rel)
            base_bytes = _read_bytes(self.base_root / rel)
            staged_bytes = _read_bytes(self.staged_root / rel)
            base_text = _decode(base_bytes)
            staged_text = _decode(staged_bytes)
            if base is not None and staged is None:
                change = FileChange(rel, Status.DELETED, base, None, _file_diff(rel, base_text, staged_text))
                for qualname in base.symbols:
                    change.symbols[qualname] = (Status.DELETED, self._symbol_diff(base, None, qualname))
                for module in base.imports:
                    change.imports[module] = Status.DELETED
                for target in base.references:
                    change.references[target] = Status.DELETED
            elif base is None and staged is not None:
                change = FileChange(rel, Status.ADDED, None, staged, _file_diff(rel, base_text, staged_text))
                for qualname in staged.symbols:
                    change.symbols[qualname] = (Status.ADDED, self._symbol_diff(None, staged, qualname))
                for module in staged.imports:
                    change.imports[module] = Status.ADDED
                for target in staged.references:
                    change.references[target] = Status.ADDED
            elif base_bytes is not None and base_bytes == staged_bytes:
                change = FileChange(rel, Status.UNCHANGED, base, staged, "")
                for qualname in staged.symbols:
                    change.symbols[qualname] = (Status.UNCHANGED, "")
                for module in staged.imports:
                    change.imports[module] = Status.UNCHANGED
                for target in staged.references:
                    change.references[target] = Status.UNCHANGED
            else:
                change = FileChange(rel, Status.MODIFIED, base, staged, _file_diff(rel, base_text, staged_text))
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
                for module in sorted(base.imports | staged.imports):
                    in_base, in_staged = module in base.imports, module in staged.imports
                    if in_base and not in_staged:
                        change.imports[module] = Status.DELETED
                    elif in_staged and not in_base:
                        change.imports[module] = Status.ADDED
                    else:
                        change.imports[module] = Status.UNCHANGED
                for target in sorted(base.references | staged.references):
                    in_base, in_staged = target in base.references, target in staged.references
                    if in_base and not in_staged:
                        change.references[target] = Status.DELETED
                    elif in_staged and not in_base:
                        change.references[target] = Status.ADDED
                    else:
                        change.references[target] = Status.UNCHANGED
            change.source = staged_text if staged_text is not None else base_text
            change.base_source = base_text
            change.staged_source = staged_text
            changes[rel] = change
        return changes

    def _index_tree(self, root: Path) -> dict[str, FileIndex]:
        indexed: dict[str, FileIndex] = {}
        for path, rel in (*iter_python_files(root), *iter_markdown_files(root)):
            extractor = self._markdown_extractor if rel.endswith(".md") else self._python_extractor
            mtime_ns, size = file_fingerprint(path)
            key = (str(root), rel, mtime_ns, size)
            cached = self._index_cache.get(key)
            if cached is None:
                cached = extractor.extract(path, rel)
                self._index_cache[key] = cached
            indexed[rel] = cached
        return indexed

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


def _file_diff(rel: str, base_text: str | None, staged_text: str | None) -> str:
    return "".join(
        difflib.unified_diff(
            (base_text or "").splitlines(keepends=True),
            (staged_text or "").splitlines(keepends=True),
            fromfile=f"base/{rel}",
            tofile=f"staged/{rel}",
        )
    )


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def _decode(raw: bytes | None) -> str | None:
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
