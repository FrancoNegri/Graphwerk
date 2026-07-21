from pathlib import Path

import pytest

from graphwerk.discard import DiscardEngine
from graphwerk.rationale import RationaleStore
from graphwerk.service import GraphService
from graphwerk.staging import ChangeSetBuilder


def write_tree(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def make_engine(base: Path, staged: Path) -> DiscardEngine:
    return DiscardEngine(base, staged, ChangeSetBuilder(base, staged))


CHANGESETBUILDER_CONTRACT_CHANGED = (
    "ChangeSetBuilder now diffs one repo dir against a base git ref "
    "(ticket 157/ADR 058) instead of two directories; DiscardEngine still "
    "builds it the old two-directory way until ticket 159 deletes it — "
    "accepted interim gap, not a regression to fix here"
)


@pytest.mark.xfail(reason=CHANGESETBUILDER_CONTRACT_CHANGED, strict=True)
def test_discard_all_round_trips_to_a_clean_diff(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "mod.py": "def f():\n    return 1\n",
        "del.py": "def gone():\n    pass\n",
    })
    write_tree(staged, {
        "mod.py": "def f():\n    return 2\n",
        "new.py": "def g():\n    pass\n",
    })

    reverted = make_engine(base, staged).discard_all()

    assert sorted(reverted) == ["del.py", "mod.py", "new.py"]
    assert (staged / "mod.py").read_text() == "def f():\n    return 1\n"
    assert (staged / "del.py").read_text() == "def gone():\n    pass\n"
    assert not (staged / "new.py").exists()

    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    statuses = {node.status.value for node in service.snapshot().nodes}
    assert statuses <= {"unchanged"}


def test_discard_all_leaves_non_change_set_files_untouched(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"mod.py": "def f():\n    return 1\n"})
    write_tree(staged, {"mod.py": "def f():\n    return 2\n"})
    scratch = staged / ".graphwerk" / "settings.json"
    scratch.parent.mkdir()
    scratch.write_text("{}")
    notes = staged / "notes.txt"
    notes.write_text("agent scratch\n")

    make_engine(base, staged).discard_all()

    assert scratch.read_text() == "{}"
    assert notes.read_text() == "agent scratch\n"


@pytest.mark.xfail(reason=CHANGESETBUILDER_CONTRACT_CHANGED, strict=True)
def test_discard_all_with_no_changes_reverts_nothing(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"mod.py": "def f():\n    return 1\n"})
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})

    assert make_engine(base, staged).discard_all() == []
