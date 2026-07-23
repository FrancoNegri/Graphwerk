import subprocess
from pathlib import Path

from graphwerk.history import changed_files_for_commits, commits_for_ticket


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def commit(repo: Path, message: str, files: dict[str, str]) -> str:
    for rel, source in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    return repo


def test_commits_for_ticket_matches_only_the_exact_ticket_number(tmp_path):
    repo = make_repo(tmp_path)
    ticket_1_sha = commit(repo, "Ticket 1: add foo", {"foo.py": "x = 1\n"})
    commit(repo, "Ticket 12: add baz", {"baz.py": "z = 1\n"})

    shas = commits_for_ticket(repo, 1)

    assert shas == [ticket_1_sha]


def test_commits_for_ticket_collects_every_matching_commit(tmp_path):
    repo = make_repo(tmp_path)
    first = commit(repo, "Ticket 2: add bar", {"bar.py": "y = 1\n"})
    second = commit(repo, "Ticket 2: follow-up for bar", {"bar.py": "y = 2\n"})
    commit(repo, "Unrelated: touch baz", {"baz.py": "z = 1\n"})

    shas = commits_for_ticket(repo, 2)

    assert set(shas) == {first, second}


def test_commits_for_ticket_is_empty_for_a_ticket_with_no_commits(tmp_path):
    repo = make_repo(tmp_path)
    commit(repo, "Ticket 1: add foo", {"foo.py": "x = 1\n"})

    assert commits_for_ticket(repo, 999) == []


def test_commits_for_ticket_is_empty_for_a_non_git_directory(tmp_path):
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()

    assert commits_for_ticket(not_a_repo, 1) == []


def test_commits_for_ticket_is_empty_for_a_repo_with_no_commits(tmp_path):
    repo = make_repo(tmp_path)

    assert commits_for_ticket(repo, 1) == []


def test_changed_files_for_commits_returns_repo_root_relative_paths_unioned(tmp_path):
    repo = make_repo(tmp_path)
    first = commit(repo, "Ticket 3: add nested module", {"pkg/mod.py": "a = 1\n"})
    second = commit(repo, "Ticket 3: add top-level file", {"top.py": "b = 1\n"})

    changed = changed_files_for_commits(repo, [first, second])

    assert changed == {"pkg/mod.py", "top.py"}


def test_changed_files_for_commits_is_empty_for_no_shas(tmp_path):
    repo = make_repo(tmp_path)
    commit(repo, "Ticket 1: add foo", {"foo.py": "x = 1\n"})

    assert changed_files_for_commits(repo, []) == set()
