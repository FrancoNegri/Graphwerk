"""File enumeration shared by the indexer, differ, and state hash.

Git-managed trees enumerate via `git ls-files` so .gitignore is respected
exactly; non-git trees (any plain directory pair) fall back to an rglob
walk with a fixed ignore list.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".graphwerk",
    ".idea",
    ".vscode",
}


def file_fingerprint(path: Path) -> tuple[int, int]:
    """(mtime_ns, size) identity used to detect whether a file's content may
    have changed without reading it — same idiom GraphService.state_hash()
    uses for its whole-tree digest."""
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def iter_python_files(root: Path):
    """Yield (abs_path, rel_path) for indexable .py files under root."""
    return iter_files_with_extension(root, ".py")


def iter_markdown_files(root: Path):
    """Yield (abs_path, rel_path) for indexable .md files under root."""
    return iter_files_with_extension(root, ".md")


def iter_files_with_extension(root: Path, extension: str):
    """Yield (abs_path, rel_path) for indexable files under root matching
    extension (git-aware: .gitignore respected, tracked + untracked, same
    symlink handling as the extension-specific wrappers above)."""
    rel_paths = _git_listed_files(root, extension)
    if rel_paths is None:
        rel_paths = _fallback_files(root, extension)
    for rel in rel_paths:
        path = root / rel
        if not path.is_file() or _crosses_symlink(root, rel):
            continue
        yield path, rel


def _crosses_symlink(root: Path, rel: str) -> bool:
    """True when the file itself, or any directory between root and it, is a symlink."""
    current = root
    for part in rel.split("/"):
        current = current / part
        if current.is_symlink():
            return True
    return False


def _git_listed_files(root: Path, extension: str) -> list[str] | None:
    """Relative paths matching extension per git (tracked + untracked,
    .gitignore applied), or None when root is not inside a git work tree."""
    command = [
        "git", "-C", str(root),
        "ls-files", "--cached", "--others", "--exclude-standard", "-z",
        "--", f"*{extension}",
    ]
    try:
        listing = subprocess.run(command, capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return sorted(rel for rel in listing.stdout.decode("utf-8").split("\0") if rel)


def _fallback_files(root: Path, extension: str) -> list[str]:
    rel_paths = []
    for path in sorted(root.rglob(f"*{extension}")):
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS or part.startswith(".") for part in rel_parts[:-1]):
            continue
        rel_paths.append(path.relative_to(root).as_posix())
    return rel_paths
