import subprocess
from pathlib import Path

from graphwerk.refs import list_refs


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", message, "--allow-empty")
    return _git(repo, "rev-parse", "HEAD").strip()


def make_repo_with_branch_and_tag(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    commit(repo, "first")
    commit(repo, "second")
    third = commit(repo, "third")
    _git(repo, "tag", "v1.0")
    _git(repo, "branch", "feature-x")
    return repo


def test_list_refs_includes_branches_tags_and_recent_commits(tmp_path):
    repo = make_repo_with_branch_and_tag(tmp_path)

    refs = list_refs(repo)

    kinds = {entry["kind"] for entry in refs}
    assert kinds == {"branch", "tag", "commit"}

    branch_names = {entry["ref"] for entry in refs if entry["kind"] == "branch"}
    assert branch_names == {"main", "feature-x"}

    tag_names = {entry["ref"] for entry in refs if entry["kind"] == "tag"}
    assert tag_names == {"v1.0"}

    commit_messages = [entry["label"] for entry in refs if entry["kind"] == "commit"]
    assert len(commit_messages) == 3
    assert any("third" in label for label in commit_messages)
    assert any("second" in label for label in commit_messages)
    assert any("first" in label for label in commit_messages)


def test_list_refs_caps_commits_at_the_requested_limit(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    for index in range(5):
        commit(repo, f"commit {index}")

    refs = list_refs(repo, recent_commit_limit=2)

    commit_entries = [entry for entry in refs if entry["kind"] == "commit"]
    assert len(commit_entries) == 2


def test_list_refs_is_empty_for_a_non_git_directory(tmp_path):
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()

    assert list_refs(not_a_repo) == []


def test_list_refs_is_empty_for_a_repo_with_no_commits(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")

    assert list_refs(repo) == []
