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
