import subprocess
from pathlib import Path

import pytest

from graphwerk.apply import ApplyEngine
from graphwerk.approval import ApprovalStore
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


def approving_store(staged: Path, *approved_paths: str) -> ApprovalStore:
    store = ApprovalStore(staged)
    for rel_path in approved_paths:
        store.approve(rel_path)
    return store


def make_engine(base: Path, staged: Path, approval_store: ApprovalStore) -> CommitEngine:
    return CommitEngine(base, ApplyEngine(base, staged), ChangeSetBuilder(base, staged), approval_store)


def test_commit_all_applies_changes_and_commits_them(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {
        "mod.py": "def f():\n    return 2\n",
        "new.py": "def g():\n    pass\n",
    })
    approval_store = approving_store(staged, "mod.py", "new.py")

    result = make_engine(base, staged, approval_store).commit_all("Bump f and add g")

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
    approval_store = approving_store(staged, "gone.py")

    result = make_engine(base, staged, approval_store).commit_all("Remove gone.py")

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
    approval_store = approving_store(staged, "mod.py")

    result = make_engine(base, staged, approval_store).commit_all("Bump f only")

    assert result["paths"] == ["mod.py"]
    assert git(base, "status", "--porcelain") == "M notes.txt"


def test_non_git_base_is_rejected_before_any_apply(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"mod.py": "def f():\n    return 1\n"})
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})
    approval_store = approving_store(staged, "mod.py")

    with pytest.raises(CommitError, match="git repository"):
        make_engine(base, staged, approval_store).commit_all("msg")
    assert (base / "mod.py").read_text() == "def f():\n    return 1\n"


def test_empty_message_is_rejected(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})
    approval_store = approving_store(staged, "mod.py")

    with pytest.raises(CommitError, match="message"):
        make_engine(base, staged, approval_store).commit_all("   ")
    assert (base / "mod.py").read_text() == "def f():\n    return 1\n"


def test_empty_change_set_is_rejected(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    approval_store = ApprovalStore(staged)

    with pytest.raises(CommitError, match="change set"):
        make_engine(base, staged, approval_store).commit_all("msg")


def test_commit_all_rejects_when_changes_exist_but_nothing_is_approved(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})
    approval_store = ApprovalStore(staged)

    with pytest.raises(CommitError, match="nothing approved"):
        make_engine(base, staged, approval_store).commit_all("msg")
    assert (base / "mod.py").read_text() == "def f():\n    return 1\n"


def test_commit_all_only_commits_the_approved_subset(tmp_path):
    base = make_git_base(tmp_path, {
        "a.py": "def a():\n    return 1\n",
        "b.py": "def b():\n    return 1\n",
    })
    staged = tmp_path / "staged"
    write_tree(staged, {
        "a.py": "def a():\n    return 2\n",
        "b.py": "def b():\n    return 2\n",
    })
    approval_store = approving_store(staged, "a.py")

    result = make_engine(base, staged, approval_store).commit_all("Bump a only")

    assert result["paths"] == ["a.py"]
    assert (base / "a.py").read_text() == "def a():\n    return 2\n"
    assert (base / "b.py").read_text() == "def b():\n    return 1\n"
    assert git(base, "status", "--porcelain") == ""


def test_commit_all_silently_excludes_an_approved_path_reverted_to_match_base(tmp_path):
    base = make_git_base(tmp_path, {
        "a.py": "def a():\n    return 1\n",
        "b.py": "def b():\n    return 1\n",
    })
    staged = tmp_path / "staged"
    write_tree(staged, {
        "a.py": "def a():\n    return 2\n",
        "b.py": "def b():\n    return 1\n",  # approved earlier, since reverted back to base
    })
    approval_store = approving_store(staged, "a.py", "b.py")

    result = make_engine(base, staged, approval_store).commit_all("Bump a only")

    assert result["paths"] == ["a.py"]


def test_commit_all_clears_the_committed_approvals_on_success(tmp_path):
    base = make_git_base(tmp_path, {
        "a.py": "def a():\n    return 1\n",
        "b.py": "def b():\n    return 1\n",
    })
    staged = tmp_path / "staged"
    write_tree(staged, {
        "a.py": "def a():\n    return 2\n",
        "b.py": "def b():\n    return 2\n",
    })
    approval_store = approving_store(staged, "a.py")

    make_engine(base, staged, approval_store).commit_all("Bump a only")

    assert approval_store.approved_paths() == set()


def test_commit_all_does_not_clear_approvals_when_it_raises(tmp_path):
    base = make_git_base(tmp_path, {"mod.py": "def f():\n    return 1\n"})
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})
    approval_store = approving_store(staged, "mod.py")

    with pytest.raises(CommitError):
        make_engine(base, staged, approval_store).commit_all("   ")

    assert approval_store.approved_paths() == {"mod.py"}
