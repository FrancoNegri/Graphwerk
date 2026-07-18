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


def build_changes(tmp_path: Path, base: dict[str, str], staged: dict[str, str]):
    for root_name, files in (("base", base), ("staged", staged)):
        root = tmp_path / root_name
        root.mkdir(exist_ok=True)
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    return ChangeSetBuilder(tmp_path / "base", tmp_path / "staged").build()


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
    for root_name in ("base", "staged"):
        root = tmp_path / root_name
        root.mkdir()
        (root / "junk.py").write_bytes(b"\xff\xfe\x00 not utf-8 \xff")
    changes = ChangeSetBuilder(tmp_path / "base", tmp_path / "staged").build()

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


def test_second_build_call_does_not_reparse_unchanged_files(tmp_path, monkeypatch):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    for root in (base, staged):
        root.mkdir()
        (root / "a.py").write_text("def f():\n    return 1\n")

    calls = spy_on_extract(monkeypatch)
    builder = ChangeSetBuilder(base, staged)
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    for root in (base, staged):
        root.mkdir()
        (root / "a.py").write_text("def f():\n    return 1\n")
        (root / "b.py").write_text("def g():\n    return 1\n")

    calls = spy_on_extract(monkeypatch)
    builder = ChangeSetBuilder(base, staged)
    builder.build()
    calls.clear()

    (staged / "a.py").write_text("def f():\n    return 1\n    # a longer body now\n")
    builder.build()

    assert calls == ["a.py"]
