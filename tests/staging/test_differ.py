from pathlib import Path

from graphwerk.staging import ChangeSetBuilder


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


def test_file_missing_on_both_sides_yields_none_source(tmp_path):
    (tmp_path / "base").mkdir()
    (tmp_path / "staged").mkdir()
    builder = ChangeSetBuilder(tmp_path / "base", tmp_path / "staged")
    assert builder._file_source("vanished.py") is None
