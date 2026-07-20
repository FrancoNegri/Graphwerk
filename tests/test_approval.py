from pathlib import Path

from graphwerk.approval import ApprovalStore


def write_tree(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def test_approved_path_is_approved(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    store = ApprovalStore(staged)

    store.approve("mod.py")

    assert store.is_approved("mod.py") is True


def test_never_approved_path_is_not_approved(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    store = ApprovalStore(staged)

    assert store.is_approved("mod.py") is False


def test_unapproved_path_is_not_approved(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    store = ApprovalStore(staged)
    store.approve("mod.py")

    store.unapprove("mod.py")

    assert store.is_approved("mod.py") is False


def test_unapprove_a_path_never_approved_is_a_no_op(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    store = ApprovalStore(staged)

    store.unapprove("mod.py")  # must not raise

    assert store.is_approved("mod.py") is False


def test_approval_evaporates_when_staged_file_changes_after_approval(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    store = ApprovalStore(staged)
    store.approve("mod.py")

    (staged / "mod.py").write_text("def f():\n    return 2\n" * 50)  # force a size change

    assert store.is_approved("mod.py") is False


def test_approved_paths_returns_only_currently_matching_approvals(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"a.py": "a = 1\n", "b.py": "b = 1\n"})
    store = ApprovalStore(staged)
    store.approve("a.py")
    store.approve("b.py")

    (staged / "b.py").write_text("b = 1\n" * 50)

    assert store.approved_paths() == {"a.py"}


def test_clear_removes_exactly_the_given_paths(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"a.py": "a = 1\n", "b.py": "b = 1\n"})
    store = ApprovalStore(staged)
    store.approve("a.py")
    store.approve("b.py")

    store.clear(["a.py"])

    assert store.approved_paths() == {"b.py"}


def test_clear_all_removes_every_approval(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"a.py": "a = 1\n", "b.py": "b = 1\n"})
    store = ApprovalStore(staged)
    store.approve("a.py")
    store.approve("b.py")

    store.clear_all()

    assert store.approved_paths() == set()


def test_reapproving_after_a_content_change_is_treated_as_fresh(tmp_path):
    staged = tmp_path / "staged"
    write_tree(staged, {"mod.py": "def f():\n    return 1\n"})
    store = ApprovalStore(staged)
    store.approve("mod.py")

    (staged / "mod.py").write_text("def f():\n    return 2\n" * 50)
    assert store.is_approved("mod.py") is False

    store.approve("mod.py")

    assert store.is_approved("mod.py") is True


def test_approving_a_path_whose_staged_file_does_not_exist_is_approved_until_recreated(tmp_path):
    """Deleted-status files: the staged copy is gone (that's what "deleted"
    means), so approval must be trackable even though there's nothing to
    stat. A missing file is its own stable fingerprint; approval only
    evaporates if the path comes back with content."""
    staged = tmp_path / "staged"
    staged.mkdir()
    store = ApprovalStore(staged)

    store.approve("gone.py")

    assert store.is_approved("gone.py") is True

    (staged / "gone.py").write_text("resurrected\n")

    assert store.is_approved("gone.py") is False
