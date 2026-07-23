"""Symbol-level diff between two revisions of a repo.

Rather than mapping textual hunks onto symbols, both versions of each file are
parsed and symbols are compared by qualified name — sidestepping hunk/symbol
alignment entirely (docs/03-architecture-notes.md, hard problem #1). Each side
of the comparison is a `Revision`: `GitRefRevision` reads via git plumbing
(`git show <ref>:<path>`) instead of a second directory walk (ADR 058);
`WorkingTreeRevision` reads whatever's on disk. `ChangeSetBuilder` doesn't
care which is which — see docs/tickets/170.
"""

from __future__ import annotations

import difflib
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from graphwerk.indexing.markdown import MarkdownExtractor
from graphwerk.indexing.python_ast import PythonAstExtractor
from graphwerk.indexing.walk import file_fingerprint, iter_files_with_extension
from graphwerk.models import FileIndex, Status

INDEXABLE_EXTENSIONS = (".py", ".md")


class Revision(Protocol):
    """One side of a comparison: a set of relative paths, and the raw bytes
    at each. Nothing about parsing or diffing — that stays in
    `ChangeSetBuilder`, which is the only thing that knows about symbols."""

    def paths(self, extensions: tuple[str, ...]) -> frozenset[str]:
        """Relative paths in this revision whose name ends in one of `extensions`."""
        ...

    def read_bytes(self, rel: str) -> bytes | None:
        """Raw content of `rel` in this revision, or None if it doesn't exist here."""
        ...

    def index_key(self, rel: str) -> object:
        """A cache key that changes whenever the parsed `FileIndex` for `rel`
        might need recomputing. Immutable revisions can key on the path
        alone; a revision whose content can change between builds (the
        working tree) must fold in a freshness signal."""
        ...


class GitRefRevision:
    """A revision pinned to a git ref, read via `git ls-tree`/`git show`
    plumbing instead of a real directory (ADR 058). A commit's content never
    changes, so both paths and bytes are cached for this instance's
    lifetime once read."""

    def __init__(self, repo_root: Path, ref: str):
        self.repo_root = repo_root
        self.ref = ref
        self._paths_cache: dict[tuple[str, ...], frozenset[str]] = {}
        self._bytes_cache: dict[str, bytes | None] = {}

    def paths(self, extensions: tuple[str, ...]) -> frozenset[str]:
        if extensions not in self._paths_cache:
            self._paths_cache[extensions] = frozenset(_git_ls_tree(self.repo_root, self.ref, extensions))
        return self._paths_cache[extensions]

    def read_bytes(self, rel: str) -> bytes | None:
        if rel not in self._bytes_cache:
            self._bytes_cache[rel] = _git_show_bytes(self.repo_root, self.ref, rel)
        return self._bytes_cache[rel]

    def index_key(self, rel: str) -> object:
        return rel


class WorkingTreeRevision:
    """The live working directory on disk (ADR 058: the developer's own
    checkout, never a graphwerk-owned copy). Always read fresh — the whole
    point of this revision is that its content can change between builds."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def paths(self, extensions: tuple[str, ...]) -> frozenset[str]:
        found: set[str] = set()
        for extension in extensions:
            found.update(rel for _, rel in iter_files_with_extension(self.repo_root, extension))
        return frozenset(found)

    def read_bytes(self, rel: str) -> bytes | None:
        return _read_bytes(self.repo_root / rel)

    def index_key(self, rel: str) -> object:
        return (rel, *file_fingerprint(self.repo_root / rel))


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
        # (this ticket's Decision-line ADR target rel_path, status), or
        # None if neither side has one (ADR 065)
        self.decision_ref: tuple[str, Status] | None = None
        # full staged text (base text for deleted files); None if unreadable
        self.source: str | None = None
        self.base_source: str | None = None
        self.staged_source: str | None = None


class ChangeSetBuilder:
    def __init__(self, repo_root: Path, base: Revision, staged: Revision):
        self.repo_root = repo_root
        self.base = base
        self.staged = staged
        self._python_extractor = PythonAstExtractor()
        self._markdown_extractor = MarkdownExtractor()
        # Revision.index_key(rel) -> FileIndex, one cache per side (a rel
        # path can carry different content on each side, so the namespaces
        # must stay separate). Unbounded for the process lifetime (ADR 019,
        # out of scope: eviction/memory bounds). Keyed by each revision's own
        # index_key rather than bare rel_path, since a WorkingTreeRevision's
        # key folds in mtime/size to catch on-disk edits, while a
        # GitRefRevision's key is just the path — its content can't change
        # for the builder's lifetime (docs/tickets/170).
        self._index_cache: dict[object, FileIndex] = {}
        self._base_index_cache: dict[object, FileIndex] = {}

    def build(self) -> dict[str, FileChange]:
        base_files = self._index_base()
        staged_files = self._index_staged()
        changes: dict[str, FileChange] = {}

        for rel in sorted(set(base_files) | set(staged_files)):
            base, staged = base_files.get(rel), staged_files.get(rel)
            base_bytes = self.base.read_bytes(rel)
            staged_bytes = self.staged.read_bytes(rel)
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
            change.decision_ref = _decision_ref_change(base, staged)
            change.source = staged_text if staged_text is not None else base_text
            change.base_source = base_text
            change.staged_source = staged_text
            changes[rel] = change
        return changes

    def _index_staged(self) -> dict[str, FileIndex]:
        return self._index(self.staged, self._index_cache)

    def _index_base(self) -> dict[str, FileIndex]:
        return self._index(self.base, self._base_index_cache)

    def _index(self, revision: Revision, cache: dict[object, FileIndex]) -> dict[str, FileIndex]:
        indexed: dict[str, FileIndex] = {}
        for rel in revision.paths(INDEXABLE_EXTENSIONS):
            key = revision.index_key(rel)
            cached = cache.get(key)
            if cached is None:
                cached = self._extract(rel, revision)
                cache[key] = cached
            indexed[rel] = cached
        return indexed

    def _extract(self, rel: str, revision: Revision) -> FileIndex:
        """Reads straight off disk for a `WorkingTreeRevision` (a real path
        exists, so the extractor's own read/decode/parse-error handling runs
        as-is); any other revision has no real path of its own, so its bytes
        get materialized to a temp file instead (`_extract_from_bytes`)."""
        if isinstance(revision, WorkingTreeRevision):
            return self._extract_at(self.repo_root / rel, rel)
        raw = revision.read_bytes(rel)
        return self._extract_from_bytes(rel, raw) if raw is not None else FileIndex(rel_path=rel)

    def _extract_from_bytes(self, rel: str, raw: bytes) -> FileIndex:
        """Materializes a git blob to a temp file so the extractor's own
        read/decode/parse-error handling runs identically to a disk read —
        the base ref has no real path of its own to hand it instead. That
        temp path has no relation to the repo's own layout, so `repo_root`
        is always passed explicitly (`_extract_at`) rather than derived from
        it (ticket 198)."""
        with tempfile.NamedTemporaryFile(suffix=Path(rel).suffix, delete=False) as handle:
            handle.write(raw)
            tmp_path = Path(handle.name)
        try:
            return self._extract_at(tmp_path, rel)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _extract_at(self, file_path: Path, rel: str) -> FileIndex:
        if rel.endswith(".md"):
            return self._markdown_extractor.extract(file_path, rel, self.repo_root)
        return self._python_extractor.extract(file_path, rel)

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


def _decision_ref_change(base: FileIndex | None, staged: FileIndex | None) -> tuple[str, Status] | None:
    """Single-valued counterpart to the `references`/`imports` set diffing
    above: a ticket names exactly one ADR (or none), never a set of them,
    so there's nothing to iterate — just compare the one value each side
    carries."""
    base_target = base.decision_ref if base else None
    staged_target = staged.decision_ref if staged else None
    if staged_target is not None:
        status = Status.UNCHANGED if staged_target == base_target else Status.ADDED
        return staged_target, status
    if base_target is not None:
        return base_target, Status.DELETED
    return None


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
