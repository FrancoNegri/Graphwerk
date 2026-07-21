import subprocess
from pathlib import Path

from graphwerk.indexing.python_ast import PythonAstExtractor
from graphwerk.models import Status
from graphwerk.staging import ChangeSetBuilder


def spy_on_extract(monkeypatch) -> list[str]:
    """Records each rel_path PythonAstExtractor.extract is called for."""
    calls: list[str] = []
    original = PythonAstExtractor.extract

    def wrapped(self, file_path, rel_path):
        calls.append(rel_path)
        return original(self, file_path, rel_path)

    monkeypatch.setattr(PythonAstExtractor, "extract", wrapped)
    return calls


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout


def commit_repo(repo: Path) -> str:
    """(Re)commits the repo's current contents as its base ref, returning the commit sha."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.email=test@graphwerk.local", "-c", "user.name=test",
         "commit", "-q", "-m", "base", "--allow-empty")
    return _git(repo, "rev-parse", "HEAD").strip()


def build_changes(tmp_path: Path, base: dict[str, str], staged: dict[str, str]):
    """Commits `base` as the base ref, then rewrites the working tree to
    `staged` (paths in `base` but not `staged` are deleted from disk,
    simulating an on-disk removal)."""
    repo = tmp_path / "repo"
    write_tree(repo, base)
    base_ref = commit_repo(repo)
    for rel in set(base) - set(staged):
        (repo / rel).unlink()
    write_tree(repo, staged)
    return ChangeSetBuilder(repo, base_ref).build()


def test_modified_file_change_carries_staged_text(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "def f():\n    return 1\n"},
        staged={"a.py": "def f():\n    return 2\n"},
    )
    assert changes["a.py"].source == "def f():\n    return 2\n"


def test_unchanged_file_change_carries_staged_text(tmp_path):
    text = "def f():\n    pass\n"
    changes = build_changes(tmp_path, base={"a.py": text}, staged={"a.py": text})
    assert changes["a.py"].source == text


def test_added_file_change_carries_staged_text(tmp_path):
    changes = build_changes(tmp_path, base={}, staged={"new.py": "x = 1\n"})
    assert changes["new.py"].source == "x = 1\n"


def test_deleted_file_change_carries_base_text(tmp_path):
    changes = build_changes(tmp_path, base={"old.py": "x = 1\n"}, staged={})
    assert changes["old.py"].source == "x = 1\n"


def test_modified_file_carries_both_full_texts(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "def f():\n    return 1\n"},
        staged={"a.py": "def f():\n    return 2\n"},
    )
    change = changes["a.py"]
    assert change.base_source == "def f():\n    return 1\n"
    assert change.staged_source == "def f():\n    return 2\n"


def test_added_file_has_no_base_source(tmp_path):
    changes = build_changes(tmp_path, base={}, staged={"new.py": "x = 1\n"})

    change = changes["new.py"]
    assert change.base_source is None
    assert change.staged_source == "x = 1\n"


def test_deleted_file_has_no_staged_source(tmp_path):
    changes = build_changes(tmp_path, base={"old.py": "x = 1\n"}, staged={})

    change = changes["old.py"]
    assert change.base_source == "x = 1\n"
    assert change.staged_source is None


def test_undecodable_file_yields_none_sources_without_raising(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "junk.py").write_bytes(b"\xff\xfe\x00 not utf-8 \xff")
    base_ref = commit_repo(repo)
    changes = ChangeSetBuilder(repo, base_ref).build()

    change = changes["junk.py"]
    assert change.base_source is None
    assert change.staged_source is None
    assert change.source is None


def test_markdown_file_is_indexed_for_headings(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"doc.md": "# Title\n\n## Context\nold body\n"},
        staged={"doc.md": "# Title\n\n## Context\nnew body\n"},
    )

    assert list(changes["doc.md"].symbols) == ["Context"]
    assert changes["doc.md"].symbols["Context"][0] == Status.MODIFIED


def test_markdown_only_tree_produces_changes(tmp_path):
    changes = build_changes(
        tmp_path,
        base={},
        staged={"doc.md": "# Title\n\n## Section\nbody\n"},
    )

    assert "doc.md" in changes
    assert changes["doc.md"].status is Status.ADDED


def test_mixed_python_and_markdown_tree_indexes_both(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "def f():\n    pass\n", "doc.md": "# Title\n\n## Notes\nbody\n"},
        staged={"a.py": "def f():\n    pass\n", "doc.md": "# Title\n\n## Notes\nbody\n"},
    )

    assert set(changes) == {"a.py", "doc.md"}
    assert changes["a.py"].status is Status.UNCHANGED
    assert changes["doc.md"].status is Status.UNCHANGED
    assert list(changes["doc.md"].symbols) == ["Notes"]


def test_added_doc_link_is_an_added_reference(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"tickets/124.md": "# Ticket\nDecision: docs/decisions/046.md\n"},
        staged={
            "tickets/124.md": (
                "# Ticket\nDecision: docs/decisions/046.md\n"
                "See [also](../decisions/047.md).\n"
            ),
        },
    )
    assert changes["tickets/124.md"].references["docs/decisions/046.md"] == Status.UNCHANGED
    assert changes["tickets/124.md"].references["decisions/047.md"] == Status.ADDED


def test_removed_doc_link_is_a_deleted_reference(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"tickets/124.md": "# Ticket\nDecision: docs/decisions/046.md\n"},
        staged={"tickets/124.md": "# Ticket\nno decision line anymore\n"},
    )
    assert changes["tickets/124.md"].references["docs/decisions/046.md"] == Status.DELETED


def test_second_build_call_does_not_reparse_unchanged_files(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "def f():\n    return 1\n"})
    base_ref = commit_repo(repo)

    calls = spy_on_extract(monkeypatch)
    builder = ChangeSetBuilder(repo, base_ref)
    builder.build()
    calls.clear()

    builder.build()

    assert calls == []


def test_modified_file_imports_split_into_added_removed_unchanged(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "import kept\nimport gone\n\ndef f():\n    pass\n"},
        staged={"a.py": "import kept\nimport fresh\n\ndef f():\n    pass\n"},
    )
    assert changes["a.py"].imports == {
        "kept": Status.UNCHANGED,
        "gone": Status.DELETED,
        "fresh": Status.ADDED,
    }


def test_added_file_imports_are_all_added(tmp_path):
    changes = build_changes(tmp_path, base={}, staged={"new.py": "import fresh\n\nx = 1\n"})
    assert changes["new.py"].imports == {"fresh": Status.ADDED}


def test_deleted_file_imports_are_all_deleted(tmp_path):
    changes = build_changes(tmp_path, base={"old.py": "import gone\n\nx = 1\n"}, staged={})
    assert changes["old.py"].imports == {"gone": Status.DELETED}


def test_unchanged_file_imports_are_all_unchanged(tmp_path):
    text = "import kept\n\nx = 1\n"
    changes = build_changes(tmp_path, base={"a.py": text}, staged={"a.py": text})
    assert changes["a.py"].imports == {"kept": Status.UNCHANGED}


def test_touching_one_file_reparses_only_that_file(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    write_tree(repo, {
        "a.py": "def f():\n    return 1\n",
        "b.py": "def g():\n    return 1\n",
    })
    base_ref = commit_repo(repo)

    calls = spy_on_extract(monkeypatch)
    builder = ChangeSetBuilder(repo, base_ref)
    builder.build()
    calls.clear()

    (repo / "a.py").write_text("def f():\n    return 1\n    # a longer body now\n")
    builder.build()

    assert calls == ["a.py"]


def test_base_ref_lists_only_paths_that_existed_at_that_commit(tmp_path):
    """A file added on disk after the base commit must not be treated as
    though it existed at the base ref (ticket 157 acceptance: new files at
    a ref that never had them are handled without error)."""
    changes = build_changes(tmp_path, base={"a.py": "x = 1\n"}, staged={"a.py": "x = 1\n", "new.py": "y = 2\n"})

    assert changes["new.py"].status is Status.ADDED
    assert changes["new.py"].base_source is None


def test_missing_base_ref_treats_every_file_as_added(tmp_path):
    """A ref that doesn't resolve (e.g. a repo with no commits, or a bogus
    ref) degrades to an empty base tree instead of raising."""
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n"})
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True, capture_output=True)

    changes = ChangeSetBuilder(repo, "HEAD").build()

    assert changes["a.py"].status is Status.ADDED
    assert changes["a.py"].base_source is None
