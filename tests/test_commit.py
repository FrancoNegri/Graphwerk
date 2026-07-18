import subprocess
from pathlib import Path

import pytest

from graphwerk.apply import ApplyEngine
from graphwerk.commit import CommitEngine, CommitError
from graphwerk.staging import ChangeSetBuilder


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def make_git_base(tmp_path: Path, files: dict[str, str]) -> Path:
    base = tmp_path / "base"
    base.mkdir()
    for rel, source in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    git(base, "init", "-q")
    git(base, "config", "user.email", "test@example.com")
    git(base, "config", "user.name", "Test")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "initial")
    return base


def write_tree(root: Path, files: dict[str, str]) -> None:
    root.mkdir(exist_ok=True)
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def make_engine(base: Path, staged: Path) -> CommitEngine:
    return CommitEngine(base, ApplyEngine(base, staged), ChangeSetBuilder(base, staged))


def test_commit_all_applies_changes_and_commits_them(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {
        "mod.py": "def f():\n    return 2\n",
        "new.py": "def g():\n    pass\n",
    })

    result = make_engine(base, staged).commit_all("Bump f and add g")

    assert sorted(result["paths"]) == ["mod.py", "new.py"]
    assert result["commit"]
    assert (base / "mod.py").read_text() == "def f():\n    return 2\n"
    assert (base / "new.py").read_text() == "def g():\n    pass\n"
    assert git(base, "log", "-1", "--format=%s") == "Bump f and add g"
    assert git(base, "status", "--porcelain") == ""


def test_commit_all_commits_a_deletion(tmp_path):
    base = make_git_base(tmp_path, {
        "keep.py": "def keep():\n    pass\n",
        "gone.py": "def gone():\n    pass\n",
    })
    staged = tmp_path / "staged"
    write_tree(staged, {"keep.py": "def keep():\n    pass\n"})

    result = make_engine(base, staged).commit_all("Remove gone.py")

    assert result["paths"] == ["gone.py"]
    assert not (base / "gone.py").exists()
    assert git(base, "status", "--porcelain") == ""


def test_commit_all_leaves_unrelated_dirty_files_out(tmp_path):
    # .txt, not .md: this asserts on a file kind the differ genuinely never
    # walks (unlike .py/.md as of ticket 125, which are diffed like any
    # other tracked file and would legitimately show up as a change).
    base = make_git_base(tmp_path, {
        "mod.py": "def f():\n    return 1\n",
        "notes.txt": "original notes\n",
    })
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})
    (base / "notes.txt").write_text("local edit outside the change set\n")

    result = make_engine(base, staged).commit_all("Bump f only")

    assert result["paths"] == ["mod.py"]
    assert git(base, "status", "--porcelain") == "M notes.txt"


def test_non_git_base_is_rejected_before_any_apply(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"mod.py": "def f():\n    return 1\n"})
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})

    with pytest.raises(CommitError, match="git repository"):
        make_engine(base, staged).commit_all("msg")
    assert (base / "mod.py").read_text() == "def f():\n    return 1\n"


def test_empty_message_is_rejected(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})

    with pytest.raises(CommitError, match="message"):
        make_engine(base, staged).commit_all("   ")
    assert (base / "mod.py").read_text() == "def f():\n    return 1\n"


def test_empty_change_set_is_rejected(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})

    with pytest.raises(CommitError, match="change set"):
        make_engine(base, staged).commit_all("msg")
