"""Snapshot-level coverage for the files -> ticket `implements` edges ADR
065 wires via graphwerk/history.py (ticket 196). Unlike test_service.py's
other fixtures (one base commit + working-tree edits), these need real
multi-commit git *history* with "Ticket NNN: ..." messages, so they build
their own repo rather than reusing make_repo/commit_repo."""

import subprocess
from pathlib import Path

from graphwerk.rationale import RationaleStore
from graphwerk.service import GraphService


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


def delete_and_commit(repo: Path, message: str, rel: str) -> str:
    (repo / rel).unlink()
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def implements_edges(snapshot) -> set[tuple[str, str]]:
    return {(edge.source, edge.target) for edge in snapshot.edges if edge.kind == "implements"}


def test_file_touched_by_a_tickets_commit_gets_an_implements_edge_to_it(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    commit(repo, "Ticket 7: add ticket doc", {
        "docs/tickets/007-add-foo.md": "## Add foo\n\nDoes a thing.\n",
    })
    base_ref = commit(repo, "Ticket 7: implement foo", {
        "foo.py": "def foo():\n    return 1\n",
    })

    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    assert ("foo.py", "docs/tickets/007-add-foo.md") in implements_edges(snapshot)


def test_a_file_from_an_unrelated_commit_gets_no_implements_edge(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    commit(repo, "Ticket 7: add ticket doc", {
        "docs/tickets/007-add-foo.md": "## Add foo\n\nDoes a thing.\n",
    })
    commit(repo, "Ticket 7: implement foo", {"foo.py": "def foo():\n    return 1\n"})
    base_ref = commit(repo, "Unrelated: touch bar", {"bar.py": "def bar():\n    return 2\n"})

    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edges = implements_edges(snapshot)
    assert ("bar.py", "docs/tickets/007-add-foo.md") not in edges
    assert not any(source == "bar.py" for source, _ in edges)


def test_ticket_with_no_matching_commits_gets_no_implements_edges(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    commit(repo, "Ticket 7: add ticket doc", {
        "docs/tickets/007-add-foo.md": "## Add foo\n\nDoes a thing.\n",
    })
    base_ref = commit(repo, "Ticket 7: implement foo", {"foo.py": "def foo():\n    return 1\n"})
    commit(repo, "Ticket 7: add unlanded ticket doc", {
        "docs/tickets/008-never-landed.md": "## Never landed\n\nNo commits reference ticket 8.\n",
    })

    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edges = implements_edges(snapshot)
    assert not any(target == "docs/tickets/008-never-landed.md" for _, target in edges)


def test_a_file_no_longer_in_the_current_snapshot_produces_no_dangling_edge(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    commit(repo, "Ticket 9: add ticket doc", {
        "docs/tickets/009-add-temp.md": "## Add temp\n\nDoes a thing.\n",
    })
    commit(repo, "Ticket 9: implement temp", {"temp.py": "def temp():\n    return 1\n"})
    base_ref = delete_and_commit(repo, "Remove temp.py", "temp.py")

    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edges = implements_edges(snapshot)
    assert not any(source == "temp.py" for source, _ in edges)
