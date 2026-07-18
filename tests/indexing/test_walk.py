import subprocess
from pathlib import Path

import pytest

from graphwerk.indexing.walk import iter_markdown_files, iter_python_files


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _rel_paths(root: Path) -> list[str]:
    return [rel for _, rel in iter_python_files(root)]


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    return repo


def test_git_root_excludes_gitignored_files(git_repo: Path) -> None:
    (git_repo / "kept.py").write_text("x = 1\n")
    (git_repo / "generated.py").write_text("x = 2\n")
    (git_repo / ".gitignore").write_text("generated.py\n")

    assert _rel_paths(git_repo) == ["kept.py"]


def test_git_root_includes_tracked_and_untracked_files(git_repo: Path) -> None:
    (git_repo / "pkg").mkdir()
    (git_repo / "pkg" / "tracked.py").write_text("x = 1\n")
    _git(git_repo, "add", "pkg/tracked.py")
    (git_repo / "untracked.py").write_text("x = 2\n")

    assert _rel_paths(git_repo) == ["pkg/tracked.py", "untracked.py"]


def test_git_root_skips_symlinked_files(git_repo: Path) -> None:
    (git_repo / "real.py").write_text("x = 1\n")
    (git_repo / "alias.py").symlink_to(git_repo / "real.py")

    assert _rel_paths(git_repo) == ["real.py"]


def test_non_git_root_skips_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    (root / "outside").mkdir(parents=True)
    (root / "outside" / "inner.py").write_text("x = 1\n")
    (root / "real.py").write_text("x = 2\n")
    (root / "alias.py").symlink_to(root / "real.py")
    (root / "linked_dir").symlink_to(root / "outside", target_is_directory=True)

    assert _rel_paths(root) == ["outside/inner.py", "real.py"]


def test_git_root_skips_files_deleted_from_disk(git_repo: Path) -> None:
    (git_repo / "kept.py").write_text("x = 1\n")
    (git_repo / "gone.py").write_text("x = 2\n")
    _git(git_repo, "add", "kept.py", "gone.py")
    (git_repo / "gone.py").unlink()

    assert _rel_paths(git_repo) == ["kept.py"]


def test_iter_markdown_files_finds_git_tracked_and_untracked_md(git_repo: Path) -> None:
    (git_repo / "README.md").write_text("# Title\n")
    _git(git_repo, "add", "README.md")
    (git_repo / "NOTES.md").write_text("# Notes\n")
    (git_repo / "kept.py").write_text("x = 1\n")

    assert [rel for _, rel in iter_markdown_files(git_repo)] == ["NOTES.md", "README.md"]


def test_iter_markdown_files_respects_gitignore(git_repo: Path) -> None:
    (git_repo / "kept.md").write_text("# Kept\n")
    (git_repo / "generated.md").write_text("# Generated\n")
    (git_repo / ".gitignore").write_text("generated.md\n")

    assert [rel for _, rel in iter_markdown_files(git_repo)] == ["kept.md"]


def test_iter_markdown_files_skips_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir(parents=True)
    (root / "real.md").write_text("# Real\n")
    (root / "alias.md").symlink_to(root / "real.md")

    assert [rel for _, rel in iter_markdown_files(root)] == ["real.md"]


def test_non_git_root_walks_like_legacy_ignore_list(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    for rel in [
        "top.py",
        "pkg/mod.py",
        "__pycache__/junk.py",
        "node_modules/dep.py",
        ".hidden/secret.py",
        "pkg/.venv/lib.py",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n")

    assert _rel_paths(root) == ["pkg/mod.py", "top.py"]
