"""Symbol-level diff between a base git ref and the working directory.

Rather than mapping textual hunks onto symbols, both versions of each file are
parsed and symbols are compared by qualified name — sidestepping hunk/symbol
alignment entirely (docs/03-architecture-notes.md, hard problem #1). "Staged"
content is simply what's on disk in `repo_root`; "base" content is read via
git plumbing (`git show <base_ref>:<path>`) instead of a second directory
walk (ADR 058).
"""

from __future__ import annotations

import difflib
import subprocess
import tempfile
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
    def __init__(self, repo_root: Path, base_ref: str):
        self.repo_root = repo_root
        self.base_ref = base_ref
        self._python_extractor = PythonAstExtractor()
        self._markdown_extractor = MarkdownExtractor()
        # (rel_path, mtime_ns, size) -> FileIndex for the working tree;
        # unbounded for the process lifetime (ADR 019, out of scope:
        # eviction/memory bounds).
        self._index_cache: dict[tuple[str, int, int], FileIndex] = {}
        # rel_path -> FileIndex for the base ref. A commit's blob content
        # never changes, so this never needs invalidating for the builder's
        # lifetime (one review session, one fixed base_ref).
        self._base_index_cache: dict[str, FileIndex] = {}
        self._base_bytes_cache: dict[str, bytes | None] = {}
        self._base_ref_paths_cache: frozenset[str] | None = None

    def build(self) -> dict[str, FileChange]:
        base_files = self._index_base_ref()
        staged_files = self._index_tree(self.repo_root)
        changes: dict[str, FileChange] = {}

        for rel in sorted(set(base_files) | set(staged_files)):
            base, staged = base_files.get(rel), staged_files.get(rel)
            base_bytes = self._base_bytes(rel)
            staged_bytes = _read_bytes(self.repo_root / rel)
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
            key = (rel, mtime_ns, size)
            cached = self._index_cache.get(key)
            if cached is None:
                cached = extractor.extract(path, rel)
                self._index_cache[key] = cached
            indexed[rel] = cached
        return indexed

    def _index_base_ref(self) -> dict[str, FileIndex]:
        indexed: dict[str, FileIndex] = {}
        for rel in self._base_ref_paths():
            cached = self._base_index_cache.get(rel)
            if cached is None:
                raw = self._base_bytes(rel)
                cached = self._extract_from_bytes(rel, raw) if raw is not None else FileIndex(rel_path=rel)
                self._base_index_cache[rel] = cached
            indexed[rel] = cached
        return indexed

    def _extract_from_bytes(self, rel: str, raw: bytes) -> FileIndex:
        """Materializes a git blob to a temp file so the extractor's own
        read/decode/parse-error handling runs identically to a disk read —
        the base ref has no real path of its own to hand it instead."""
        extractor = self._markdown_extractor if rel.endswith(".md") else self._python_extractor
        with tempfile.NamedTemporaryFile(suffix=Path(rel).suffix, delete=False) as handle:
            handle.write(raw)
            tmp_path = Path(handle.name)
        try:
            index = extractor.extract(tmp_path, rel)
        finally:
            tmp_path.unlink(missing_ok=True)
        return index

    def _base_ref_paths(self) -> frozenset[str]:
        if self._base_ref_paths_cache is None:
            self._base_ref_paths_cache = frozenset(
                _git_ls_tree(self.repo_root, self.base_ref, (".py", ".md"))
            )
        return self._base_ref_paths_cache

    def _base_bytes(self, rel: str) -> bytes | None:
        if rel not in self._base_ref_paths():
            return None
        if rel not in self._base_bytes_cache:
            self._base_bytes_cache[rel] = _git_show_bytes(self.repo_root, self.base_ref, rel)
        return self._base_bytes_cache[rel]

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


def _git_ls_tree(repo_root: Path, ref: str, extensions: tuple[str, ...]) -> list[str]:
    """Paths at `ref` matching `extensions`, or empty when `ref` doesn't
    resolve or `repo_root` isn't a git repository — same permissive posture
    as `_git_listed_files` in indexing/walk.py, generalized from "no second
    directory" to "no base ref at all"."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-tree", "-r", "--name-only", "-z", ref],
            capture_output=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return []
    names = result.stdout.decode("utf-8").split("\0")
    return [rel for rel in names if rel.endswith(extensions)]


def _git_show_bytes(repo_root: Path, ref: str, rel: str) -> bytes | None:
    """The blob content at `ref:rel`, or None when it doesn't exist there
    (the new-file case) or the read otherwise fails."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{ref}:{rel}"],
            capture_output=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    return result.stdout


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
