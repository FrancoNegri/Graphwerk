import subprocess
from pathlib import Path

from graphwerk.indexing.python_ast import PythonAstExtractor
from graphwerk.models import Status
from graphwerk.staging import ChangeSetBuilder, GitRefRevision, WorkingTreeRevision


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
    return ChangeSetBuilder(repo, GitRefRevision(repo, base_ref), WorkingTreeRevision(repo)).build()


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
    changes = ChangeSetBuilder(repo, GitRefRevision(repo, base_ref), WorkingTreeRevision(repo)).build()

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
    builder = ChangeSetBuilder(repo, GitRefRevision(repo, base_ref), WorkingTreeRevision(repo))
    builder.build()
    calls.clear()

    builder.build()

    assert calls == []


def test_git_ref_revision_on_the_staged_side_reads_that_refs_content(tmp_path, monkeypatch):
    """Regression: staged used to be read straight off disk regardless of
    which Revision it actually was (docs/tickets/171) — a `GitRefRevision`
    on the staged side must produce that commit's content, not whatever is
    currently on disk, and must never touch the working tree."""
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "def f():\n    return 1\n"})
    first_ref = commit_repo(repo)
    write_tree(repo, {"a.py": "def f():\n    return 2\n"})
    second_ref = commit_repo(repo)
    write_tree(repo, {"a.py": "def f():\n    return 3\n"})  # uncommitted, must be ignored

    changes = ChangeSetBuilder(repo, GitRefRevision(repo, first_ref), GitRefRevision(repo, second_ref)).build()

    assert changes["a.py"].staged_source == "def f():\n    return 2\n"
    # The parsed symbol table is where the old bug actually lived: it read
    # straight off disk ("return 3") regardless of which Revision was
    # passed as staged, even though staged_source/text above were already
    # correct (build() reads bytes through the Revision directly).
    assert "return 2" in changes["a.py"].staged.symbols["f"].source
    assert "return 3" not in changes["a.py"].staged.symbols["f"].source


def test_working_tree_revision_on_the_base_side_detects_edits_across_builds(tmp_path):
    """The base-side FileIndex cache used to assume the base is always
    immutable (true only for `GitRefRevision`); with a `WorkingTreeRevision`
    on the base side, a second `build()` after an on-disk edit must
    reparse rather than serve the first build's stale symbol table."""
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "def f():\n    return 1\n"})
    first_ref = commit_repo(repo)
    write_tree(repo, {"a.py": "def f():\n    return 2\n"})  # uncommitted

    builder = ChangeSetBuilder(repo, WorkingTreeRevision(repo), GitRefRevision(repo, first_ref))
    builder.build()

    (repo / "a.py").write_text("def f():\n    return 9\n")
    changes = builder.build()

    assert "return 9" in changes["a.py"].base.symbols["f"].source


def test_if_nested_function_symbol_status_added(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "if TEST_MODE:\n    pass\n"},
        staged={"a.py": "if TEST_MODE:\n    def configure():\n        pass\n"},
    )
    assert changes["a.py"].symbols["configure"][0] == Status.ADDED


def test_if_nested_function_symbol_status_deleted(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "if TEST_MODE:\n    def configure():\n        pass\n"},
        staged={"a.py": "if TEST_MODE:\n    pass\n"},
    )
    assert changes["a.py"].symbols["configure"][0] == Status.DELETED


def test_if_nested_function_symbol_status_modified(tmp_path):
    changes = build_changes(
        tmp_path,
        base={"a.py": "if TEST_MODE:\n    def configure():\n        return 1\n"},
        staged={"a.py": "if TEST_MODE:\n    def configure():\n        return 2\n"},
    )
    assert changes["a.py"].symbols["configure"][0] == Status.MODIFIED


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
    builder = ChangeSetBuilder(repo, GitRefRevision(repo, base_ref), WorkingTreeRevision(repo))
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

    changes = ChangeSetBuilder(repo, GitRefRevision(repo, "HEAD"), WorkingTreeRevision(repo)).build()

    assert changes["a.py"].status is Status.ADDED
    assert changes["a.py"].base_source is None


def test_git_ref_revision_lists_paths_and_reads_bytes_at_the_ref(tmp_path):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n", "doc.md": "# T\n"})
    ref = commit_repo(repo)
    (repo / "a.py").write_text("x = 2\n")  # uncommitted edit; ref content must not reflect it

    revision = GitRefRevision(repo, ref)

    assert revision.paths((".py", ".md")) == {"a.py", "doc.md"}
    assert revision.read_bytes("a.py") == b"x = 1\n"
    assert revision.read_bytes("doc.md") == b"# T\n"
    assert revision.read_bytes("missing.py") is None


def test_git_ref_revision_paths_filters_by_extension(tmp_path):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n", "doc.md": "# T\n"})
    ref = commit_repo(repo)

    revision = GitRefRevision(repo, ref)

    assert revision.paths((".py",)) == {"a.py"}


def test_working_tree_revision_lists_paths_and_reads_bytes_from_disk(tmp_path):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n", "doc.md": "# T\n"})

    revision = WorkingTreeRevision(repo)

    assert revision.paths((".py", ".md")) == {"a.py", "doc.md"}
    assert revision.read_bytes("a.py") == b"x = 1\n"
    assert revision.read_bytes("missing.py") is None


def test_git_ref_revision_caches_bytes_per_instance(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n"})
    ref = commit_repo(repo)
    revision = GitRefRevision(repo, ref)
    revision.read_bytes("a.py")  # warm the cache before the subprocess spy is installed

    original_run = subprocess.run
    calls: list[object] = []

    def spy(*args, **kwargs):
        calls.append(args)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    assert revision.read_bytes("a.py") == b"x = 1\n"

    assert calls == []


def test_git_ref_revision_caches_paths_per_instance(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n"})
    ref = commit_repo(repo)
    revision = GitRefRevision(repo, ref)
    revision.paths((".py",))  # warm the cache before the subprocess spy is installed

    original_run = subprocess.run
    calls: list[object] = []

    def spy(*args, **kwargs):
        calls.append(args)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    assert revision.paths((".py",)) == {"a.py"}

    assert calls == []


def test_working_tree_revision_reflects_current_disk_contents(tmp_path):
    repo = tmp_path / "repo"
    write_tree(repo, {"a.py": "x = 1\n"})
    revision = WorkingTreeRevision(repo)
    assert revision.read_bytes("a.py") == b"x = 1\n"

    (repo / "a.py").write_text("x = 2\n")

    assert revision.read_bytes("a.py") == b"x = 2\n"
