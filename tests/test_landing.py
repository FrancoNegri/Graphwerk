import subprocess
from pathlib import Path

import pytest

from graphwerk.landing import commit_all, revert_all


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def _init_repo(repo: Path, files: dict[str, str]) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", "base")


def test_commit_all_commits_only_the_given_paths(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "a = 1\n", "b.py": "b = 1\n", "c.py": "c = 1\n"})

    (repo / "a.py").write_text("a = 2\n")
    (repo / "b.py").write_text("b = 2\n")
    (repo / "new.py").write_text("new = 1\n")
    (repo / "c.py").write_text("c = 2\n")

    commit_all(repo, ["a.py", "b.py", "new.py"], "landed changes")

    assert _git(repo, "log", "-1", "--format=%s").strip() == "landed changes"
    status = _git(repo, "status", "--porcelain")
    dirty = {line[3:] for line in status.splitlines()}
    assert dirty == {"c.py"}


def test_commit_all_empty_paths_is_noop(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "a = 1\n"})
    (repo / "a.py").write_text("a = 2\n")

    commit_all(repo, [], "should not run")

    status = _git(repo, "status", "--porcelain")
    assert status.strip() != ""
    log = _git(repo, "log", "--format=%s")
    assert "should not run" not in log


def test_commit_all_raises_on_failure(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "a = 1\n"})
    (repo / "a.py").write_text("a = 2\n")

    with pytest.raises(subprocess.CalledProcessError):
        commit_all(repo, ["a.py"], "")


def test_revert_all_stashes_only_the_given_paths(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "a = 1\n", "b.py": "b = 1\n"})

    (repo / "a.py").write_text("a = 2\n")
    (repo / "b.py").write_text("b = 2\n")

    revert_all(repo, ["a.py"])

    assert (repo / "a.py").read_text() == "a = 1\n"
    assert (repo / "b.py").read_text() == "b = 2\n"
    stash_list = _git(repo, "stash", "list")
    assert len(stash_list.strip().splitlines()) == 1


def test_revert_all_empty_paths_is_noop(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo, {"a.py": "a = 1\n"})
    (repo / "a.py").write_text("a = 2\n")

    revert_all(repo, [])

    assert (repo / "a.py").read_text() == "a = 2\n"
    stash_list = _git(repo, "stash", "list")
    assert stash_list.strip() == ""
