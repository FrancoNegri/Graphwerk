import json
import subprocess
from pathlib import Path

from graphwerk.models import FileIndex, Status
from graphwerk.rationale import RationaleStore
from graphwerk.service import GraphService, ModuleFileResolver
from graphwerk.staging.differ import FileChange


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


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


def make_repo(tmp_path: Path, base_files: dict[str, str],
              staged_files: dict[str, str] | None = None) -> tuple[Path, str]:
    """Commits `base_files` as the base ref, then (if given) rewrites the
    working tree to `staged_files` — paths in `base_files` but not
    `staged_files` are deleted from disk, simulating an on-disk removal.
    `staged_files=None` leaves the working tree exactly as committed."""
    repo = tmp_path / "repo"
    write_tree(repo, base_files)
    base_ref = commit_repo(repo)
    if staged_files is not None:
        for rel in set(base_files) - set(staged_files):
            (repo / rel).unlink()
        write_tree(repo, staged_files)
    return repo, base_ref


def import_edges(snapshot) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in snapshot.edges if e.kind == "imports"}


def edge_between(snapshot, source: str, target: str, kind: str = "calls"):
    for edge in snapshot.edges:
        if edge.source == source and edge.target == target and edge.kind == kind:
            return edge
    raise AssertionError(f"no {kind} edge {source} -> {target}")


def without_code(via_imports: list) -> list:
    return [{key: entry[key] for key in ("module", "status")} for entry in via_imports]


def make_service(tmp_path: Path, files: dict[str, str]) -> GraphService:
    repo, base_ref = make_repo(tmp_path, files)
    return GraphService(repo, base_ref, RationaleStore(staged_root=repo))


def test_src_layout_import_resolves_to_package_root_file(tmp_path):
    service = make_service(tmp_path, {
        "src/pkg/store.py": "def save():\n    pass\n",
        "src/pkg/webhook.py": "from pkg.store import save\n\ndef handle():\n    save()\n",
    })
    assert ("src/pkg/webhook.py", "src/pkg/store.py") in import_edges(service.snapshot())


def test_package_import_resolves_to_init_file():
    resolver = ModuleFileResolver(["pkg/__init__.py", "pkg/mod.py"])
    assert resolver.resolve("pkg") == "pkg/__init__.py"


def test_package_import_resolves_to_init_file_under_src():
    resolver = ModuleFileResolver(["src/pkg/__init__.py"])
    assert resolver.resolve("pkg") == "src/pkg/__init__.py"


def test_ambiguous_module_name_resolves_to_nothing():
    resolver = ModuleFileResolver(["a/utils.py", "b/utils.py"])
    assert resolver.resolve("utils") is None


def test_exact_dotted_path_wins_over_ambiguous_suffix():
    resolver = ModuleFileResolver(["utils.py", "a/utils.py"])
    assert resolver.resolve("utils") == "utils.py"
    assert resolver.resolve("a.utils") == "a/utils.py"


def test_symbol_nodes_carry_staged_source(tmp_path):
    repo, base_ref = make_repo(
        tmp_path, {"a.py": "def f():\n    return 1\n"}, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py::f"].source == "def f():\n    return 2\n"


def test_deleted_symbol_carries_base_source(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def gone():\n    return 1\n\ndef kept():\n    pass\n"},
        {"a.py": "def kept():\n    pass\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py::gone"].source == "def gone():\n    return 1\n"


def test_file_nodes_carry_full_source_text(tmp_path):
    text = "def f():\n    pass\n"
    service = make_service(tmp_path, {"a.py": text})
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py"].source == text


def test_modified_symbol_code_interleaves_del_lines_with_spans(tmp_path):
    repo, base_ref = make_repo(
        tmp_path, {"a.py": "def f():\n    return 1\n"}, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    nodes = {n.id: n for n in service.snapshot().nodes}

    code = nodes["a.py::f"].code
    ops = [line["op"] for line in code]
    assert "del" in ops and "add" in ops and "ctx" in ops
    assert any(line["spans"] for line in code)


def test_unchanged_node_code_is_all_context(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    nodes = {n.id: n for n in service.snapshot().nodes}

    for node_id in ("a.py", "a.py::f"):
        code = nodes[node_id].code
        assert code
        assert all(line["op"] == "ctx" for line in code)


def test_added_file_nodes_code_is_all_added(tmp_path):
    repo, base_ref = make_repo(tmp_path, {}, {"new.py": "def f():\n    return 1\n"})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    nodes = {n.id: n for n in service.snapshot().nodes}

    for node_id in ("new.py", "new.py::f"):
        code = nodes[node_id].code
        assert code
        assert all(line["op"] == "add" for line in code)


def test_deleted_file_nodes_code_is_all_removed(tmp_path):
    repo, base_ref = make_repo(tmp_path, {"old.py": "def f():\n    return 1\n"}, {})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    nodes = {n.id: n for n in service.snapshot().nodes}

    for node_id in ("old.py", "old.py::f"):
        code = nodes[node_id].code
        assert code
        assert all(line["op"] == "del" for line in code)


def test_unreadable_file_node_code_is_none(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "junk.py").write_bytes(b"\xff\xfe not utf-8 \xff")
    base_ref = commit_repo(repo)
    (repo / "junk.py").write_bytes(b"\xff\xfe still not utf-8 \xff")
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["junk.py"].code is None


def test_serialized_node_carries_code_but_not_source(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    payload = service.snapshot().to_dict()

    for node in payload["nodes"]:
        assert "source" not in node
        assert "code" in node


def test_snapshot_meta_carries_rationale_status(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})

    meta = service.snapshot().meta
    assert meta["rationale"] == {
        "sidecar_path": None,
        "sidecar_entries": 0,
        "transcript_path": None,
        "transcript_entries": 0,
        "warning": None,
        "message": None,
    }


def test_snapshot_meta_message_flags_changes_without_any_rationale_source(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    repo, base_ref = make_repo(
        tmp_path, {"a.py": "def f():\n    return 1\n"}, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))

    message = service.snapshot().meta["rationale"]["message"]
    assert message is not None
    assert str(repo) in message


def write_transcript(path: Path, entries: list) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def assistant_entry(*blocks) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def edit_block(file_path: Path) -> dict:
    return {"type": "tool_use", "name": "Edit", "input": {"file_path": str(file_path)}}


def test_snapshot_marks_low_confidence_why_from_proximity_fallback(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {"business.py": "def core():\n    return 1\n", "deps.py": "def helper():\n    return 1\n"},
        {"business.py": "def core():\n    return 2\n", "deps.py": "def helper():\n    return 2\n"},
    )

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Now building the business logic module."),
            edit_block(repo / "business.py"),
            edit_block(repo / "deps.py"),
        ),
        assistant_entry(text_block("Final: `business.py` implements the core rules.")),
    ])
    rationale = RationaleStore(staged_root=repo, transcript_path=transcript)
    service = GraphService(repo, base_ref, rationale)
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["business.py"].why_confident is True
    assert nodes["deps.py"].why_confident is False


def test_snapshot_symbol_node_carries_why_confidence(tmp_path):
    repo, base_ref = make_repo(
        tmp_path, {"business.py": "def core():\n    return 1\n"}, {"business.py": "def core():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Working on it."),
            edit_block(repo / "business.py"),
        ),
        assistant_entry(text_block("Final: `core` now returns the updated value.")),
    ])
    rationale = RationaleStore(staged_root=repo, transcript_path=transcript)
    service = GraphService(repo, base_ref, rationale)
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["business.py::core"].why_confident is True


def test_unchanged_node_has_no_why_confidence(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py"].why_confident is None


def test_snapshot_marks_describes_only_why_from_a_guidance_bullet(tmp_path):
    repo, base_ref = make_repo(
        tmp_path, {"deps.py": "def helper():\n    return 1\n"}, {"deps.py": "def helper():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Working on it."),
            edit_block(repo / "deps.py"),
        ),
        assistant_entry(text_block("- `deps.py`: FastAPI dependency-injection providers.")),
    ])
    rationale = RationaleStore(staged_root=repo, transcript_path=transcript)
    service = GraphService(repo, base_ref, rationale)
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["deps.py"].why_justifies is False


def test_snapshot_marks_justifying_why_from_a_guidance_bullet(tmp_path):
    repo, base_ref = make_repo(
        tmp_path, {"flags.py": "def helper():\n    return 1\n"}, {"flags.py": "def helper():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Working on it."),
            edit_block(repo / "flags.py"),
        ),
        assistant_entry(text_block(
            "- `flags.py`: shared env-derived flags, split out since several "
            "other modules need them."
        )),
    ])
    rationale = RationaleStore(staged_root=repo, transcript_path=transcript)
    service = GraphService(repo, base_ref, rationale)
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["flags.py"].why_justifies is True


def test_unchanged_node_has_no_why_justifies(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py"].why_justifies is None


def test_calls_edge_into_modified_target_has_modified_status(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def target():\n    return 1\n\ndef caller():\n    return target()\n"},
        {"a.py": "def target():\n    return 2\n\ndef caller():\n    return target()\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::target")
    assert edge.status == Status.MODIFIED


def test_calls_edge_into_added_target_has_added_status(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def caller():\n    return 1\n"},
        {"a.py": "def caller():\n    return new_func()\n\ndef new_func():\n    return 2\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::new_func")
    assert edge.status == Status.ADDED


def calls_edge_pairs(snapshot) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in snapshot.edges if e.kind == "calls"}


def uses_edge_pairs(snapshot) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in snapshot.edges if e.kind == "uses"}


def test_unchanged_caller_does_not_resolve_to_deleted_target_it_no_longer_calls(tmp_path):
    """Mirror phantom case (ADR 032): a caller whose calls came from
    staged_info must not resolve to a deleted (base-only) target it never
    actually called in the staged tree, even if the name still matches."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def gone():\n    return 1\n\ndef caller():\n    return gone()\n"},
        {"a.py": "def caller():\n    return gone()\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    assert ("a.py::caller", "a.py::gone") not in calls_edge_pairs(snapshot)


def test_unchanged_caller_does_not_resolve_to_deleted_target_in_another_file(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "a.py": "def caller():\n    return helper()\n",
            "b.py": "def helper():\n    return 1\n",
        },
        {"a.py": "def caller():\n    return helper()\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    assert ("a.py::caller", "b.py::helper") not in calls_edge_pairs(snapshot)


def test_deleted_caller_does_not_resolve_to_added_target_with_same_name(tmp_path):
    """Phantom case (ADR 032): a deleted (base-only) caller must not resolve
    to an added (staged-only) target that only exists in the other tree,
    e.g. a relocated symbol's old and new copies sharing a simple name."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def gone():\n    return helper()\n"},
        {"b.py": "def helper():\n    return 1\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    assert ("a.py::gone", "b.py::helper") not in calls_edge_pairs(snapshot)


def test_deleted_caller_still_resolves_to_deleted_target_it_actually_called(tmp_path):
    """Regression guard (ADR 032): the deleted -> deleted pairing that
    reconstructs a gutted file's real internal wiring stays intact."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def helper():\n    return 1\n\ndef gone():\n    return helper()\n"},
        {},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::gone", "a.py::helper")
    assert edge.status == Status.DELETED


def test_if_nested_caller_deletion_surfaces_deleted_node_and_calls_edge(tmp_path):
    """Ticket 168 dogfood scenario: a caller defined inside a module-level
    `if` block must become a real node with a `deleted` status when it's
    removed, not vanish from both trees with no signal anywhere."""
    repo, base_ref = make_repo(
        tmp_path,
        {
            "webhook.py": (
                "from dependencies import get_calendar\n"
                "\n"
                "if TEST_MODE:\n"
                "    def configure_calendar_slots():\n"
                "        return get_calendar()\n"
            ),
            "dependencies.py": "def get_calendar():\n    return 1\n",
        },
        {
            "webhook.py": "from dependencies import get_calendar\n\nif TEST_MODE:\n    pass\n",
            "dependencies.py": "def get_calendar():\n    return 1\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["webhook.py::configure_calendar_slots"].status == Status.DELETED
    edge = edge_between(
        snapshot, "webhook.py::configure_calendar_slots", "dependencies.py::get_calendar"
    )
    assert edge.status == Status.DELETED


def test_class_does_not_duplicate_its_methods_calls_edge(tmp_path):
    """Ticket 169 dogfood scenario: a review showed both
    `TestOnlyRouter -> get_calendar` and `TestOnlyRouter.__init__ ->
    get_calendar` as separate edges for a single call site inside
    `__init__` (ADR 059). Only the method's edge is real."""
    service = make_service(tmp_path, {
        "webhook.py": (
            "from dependencies import get_calendar\n"
            "\n"
            "class TestOnlyRouter:\n"
            "    def __init__(self):\n"
            "        get_calendar()\n"
        ),
        "dependencies.py": "def get_calendar():\n    return 1\n",
    })
    snapshot = service.snapshot()

    pairs = calls_edge_pairs(snapshot)
    assert ("webhook.py::TestOnlyRouter.__init__", "dependencies.py::get_calendar") in pairs
    assert ("webhook.py::TestOnlyRouter", "dependencies.py::get_calendar") not in pairs


def test_calls_edge_that_causes_affected_status_keeps_targets_own_status(tmp_path):
    """The edge _mark_affected used to flip its source to AFFECTED still
    reports the target's real status, not "affected" — target status wins."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def target():\n    return 1\n\ndef caller():\n    return target()\n"},
        {"a.py": "def target():\n    return 2\n\ndef caller():\n    return target()\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["a.py::caller"].status == Status.AFFECTED
    edge = edge_between(snapshot, "a.py::caller", "a.py::target")
    assert edge.status == Status.MODIFIED


def test_calls_edge_to_unrelated_unchanged_target_has_unchanged_status(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "a.py": "def helper():\n    return 1\n\ndef runner():\n    return helper()\n",
            "b.py": "def other():\n    return 1\n",
        },
        {
            "a.py": "def helper():\n    return 1\n\ndef runner():\n    return helper()\n",
            "b.py": "def other():\n    return 2\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::runner", "a.py::helper")
    assert edge.status == Status.UNCHANGED


def test_calls_edge_from_deleted_source_to_unchanged_target_has_deleted_status(tmp_path):
    """ADR 054: a call site that no longer exists shouldn't read as
    unchanged just because the thing it used to call didn't change."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def helper():\n    return 1\n\ndef gone():\n    return helper()\n"},
        {"a.py": "def helper():\n    return 1\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["a.py::helper"].status == Status.UNCHANGED

    edge = edge_between(snapshot, "a.py::gone", "a.py::helper")
    assert edge.status == Status.DELETED


def test_calls_edge_from_added_source_to_unchanged_target_has_added_status(tmp_path):
    """ADR 054 (amended): a call site that only exists in staged shouldn't
    read as unchanged just because the thing it calls didn't change."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "def helper():\n    return 1\n"},
        {"a.py": "def helper():\n    return 1\n\ndef new_caller():\n    return helper()\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["a.py::helper"].status == Status.UNCHANGED

    edge = edge_between(snapshot, "a.py::new_caller", "a.py::helper")
    assert edge.status == Status.ADDED


def test_calls_edge_to_unrelated_target_from_affected_source_has_unchanged_status(tmp_path):
    """A caller becomes AFFECTED via its call to a modified target; a
    different, unrelated call it also makes must not borrow that label —
    only the call that actually leads into changed code should."""
    repo, base_ref = make_repo(
        tmp_path,
        {
            "a.py": (
                "def target():\n    return 1\n\n"
                "def unrelated():\n    return 1\n\n"
                "def caller():\n    target()\n    return unrelated()\n"
            ),
        },
        {
            "a.py": (
                "def target():\n    return 2\n\n"
                "def unrelated():\n    return 1\n\n"
                "def caller():\n    target()\n    return unrelated()\n"
            ),
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["a.py::caller"].status == Status.AFFECTED

    edge = edge_between(snapshot, "a.py::caller", "a.py::unrelated")
    assert edge.status == Status.UNCHANGED


def test_caller_does_not_resolve_to_same_named_symbol_in_a_file_it_does_not_import(tmp_path):
    """Agendabot shape (ADR 034): e2e_runner.py defines and calls its own
    local _format_history and does not import conversation.py at all;
    conversation.py's unrelated same-named _format_history must not wire in
    just because the simple name matches."""
    service = make_service(tmp_path, {
        "e2e_runner.py": (
            "def _format_history(entries):\n    return entries\n\n"
            "def run_e2e_scenario():\n    return _format_history([])\n"
        ),
        "conversation.py": "def _format_history(entries):\n    return entries\n",
    })
    snapshot = service.snapshot()

    pairs = calls_edge_pairs(snapshot)
    assert ("e2e_runner.py::run_e2e_scenario", "conversation.py::_format_history") not in pairs
    assert ("e2e_runner.py::run_e2e_scenario", "e2e_runner.py::_format_history") in pairs


def test_caller_resolves_to_same_named_symbol_in_a_file_it_does_import(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    assert ("caller.py::run", "helper.py::do_work") in calls_edge_pairs(snapshot)


def test_caller_resolves_to_same_named_symbol_in_its_own_file(tmp_path):
    service = make_service(tmp_path, {
        "a.py": "def helper():\n    return 1\n\ndef run():\n    return helper()\n",
    })
    snapshot = service.snapshot()

    assert ("a.py::run", "a.py::helper") in calls_edge_pairs(snapshot)


def test_call_edge_resolves_through_two_hop_reexport_chain(tmp_path):
    """Dogfood shape (ADR 048): pkg/__init__.py only re-exports Thing from
    pkg/inner.py; caller.py imports Thing from pkg (not pkg.inner) and calls
    it, so the edge only exists if reachability follows the re-export hop."""
    service = make_service(tmp_path, {
        "pkg/__init__.py": "from pkg.inner import Thing\n",
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
    })
    snapshot = service.snapshot()

    assert ("caller.py::run", "pkg/inner.py::Thing") in calls_edge_pairs(snapshot)


def test_call_edge_resolves_through_three_hop_reexport_chain(tmp_path):
    """The traversal isn't hardcoded to exactly one extra hop."""
    service = make_service(tmp_path, {
        "outer/__init__.py": "from outer.mid import Thing\n",
        "outer/mid/__init__.py": "from outer.mid.inner import Thing\n",
        "outer/mid/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from outer import Thing\n\ndef run():\n    return Thing()\n",
    })
    snapshot = service.snapshot()

    assert ("caller.py::run", "outer/mid/inner.py::Thing") in calls_edge_pairs(snapshot)


def test_multi_hop_call_edge_names_the_full_admitting_chain(tmp_path):
    """Ticket 137: a multi-hop edge's via_imports shows which module and
    file admits each hop, in order, instead of no explanation at all."""
    service = make_service(tmp_path, {
        "pkg/__init__.py": "from pkg.inner import Thing\n",
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "pkg/inner.py::Thing")
    hops = [{"module": entry["module"], "file": entry["file"]} for entry in edge.via_imports]
    assert hops == [
        {"module": "pkg", "file": "pkg/__init__.py"},
        {"module": "pkg.inner", "file": "pkg/inner.py"},
    ]


def test_multi_hop_via_imports_chain_follows_three_hops_in_order(tmp_path):
    service = make_service(tmp_path, {
        "outer/__init__.py": "from outer.mid import Thing\n",
        "outer/mid/__init__.py": "from outer.mid.inner import Thing\n",
        "outer/mid/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from outer import Thing\n\ndef run():\n    return Thing()\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "outer/mid/inner.py::Thing")
    hops = [{"module": entry["module"], "file": entry["file"]} for entry in edge.via_imports]
    assert hops == [
        {"module": "outer", "file": "outer/__init__.py"},
        {"module": "outer.mid", "file": "outer/mid/__init__.py"},
        {"module": "outer.mid.inner", "file": "outer/mid/inner.py"},
    ]


def test_multi_hop_via_imports_first_hop_still_reports_caller_code_containment(tmp_path):
    """First hop keeps the direct-import behavior (in_caller_code reflects
    the actual calling symbol's span); later hops have no enclosing symbol
    to check against, so they report False rather than crashing."""
    service = make_service(tmp_path, {
        "pkg/__init__.py": "from pkg.inner import Thing\n",
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "def run():\n    from pkg import Thing\n    return Thing()\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "pkg/inner.py::Thing")
    first_hop, second_hop = edge.via_imports
    assert first_hop["in_caller_code"] is True
    assert second_hop["in_caller_code"] is False


def test_single_hop_via_imports_shape_is_unchanged_by_multi_hop_support(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    assert without_code(edge.via_imports) == [{"module": "helper", "status": "unchanged"}]
    assert "file" not in edge.via_imports[0]


def test_caller_does_not_resolve_transitively_to_unreachable_file_with_same_named_symbol(tmp_path):
    """Extends the ADR 034 protection onto the new transitive traversal: a
    same-named symbol in a file that isn't part of any resolvable import
    chain from the caller must still not wire in."""
    service = make_service(tmp_path, {
        "pkg/__init__.py": "from pkg.inner import Thing\n",
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
        "unrelated.py": "class Thing:\n    pass\n",
    })
    snapshot = service.snapshot()

    pairs = calls_edge_pairs(snapshot)
    assert ("caller.py::run", "unrelated.py::Thing") not in pairs
    assert ("caller.py::run", "pkg/inner.py::Thing") in pairs


def test_deleted_caller_resolves_transitive_target_through_base_tree_chain(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "pkg/__init__.py": "from pkg.inner import Thing\n",
            "pkg/inner.py": "class Thing:\n    pass\n",
            "caller.py": "from pkg import Thing\n\ndef gone():\n    return Thing()\n",
        },
        {},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    assert ("caller.py::gone", "pkg/inner.py::Thing") in calls_edge_pairs(snapshot)


def test_unchanged_caller_does_not_resolve_transitively_through_base_only_hop(tmp_path):
    """Mirror of ADR 032 tree containment on the new traversal: the
    intermediate re-export file existed in base but was removed in staged,
    so a caller whose calls come from the staged tree must not resolve
    through it even though the resolver can still map the module name to
    that path."""
    repo, base_ref = make_repo(
        tmp_path,
        {
            "pkg/__init__.py": "from pkg.inner import Thing\n",
            "pkg/inner.py": "class Thing:\n    pass\n",
            "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
        },
        {
            "pkg/inner.py": "class Thing:\n    pass\n",
            "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    assert ("caller.py::run", "pkg/inner.py::Thing") not in calls_edge_pairs(snapshot)


def test_transitive_traversal_does_not_hang_on_cyclic_imports(tmp_path):
    service = make_service(tmp_path, {
        "a.py": "import b\n\ndef run():\n    return thing()\n",
        "b.py": "import a\nimport c\n",
        "c.py": "def thing():\n    return 1\n",
    })
    snapshot = service.snapshot()

    assert ("a.py::run", "c.py::thing") in calls_edge_pairs(snapshot)


def test_cross_file_calls_edge_names_added_admitting_import(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "caller.py": "def run():\n    return 1\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
        {
            "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    assert without_code(edge.via_imports) == [{"module": "helper", "status": "added"}]


def test_cross_file_calls_edge_names_unchanged_admitting_import(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    assert without_code(edge.via_imports) == [{"module": "helper", "status": "unchanged"}]


def test_same_file_calls_edge_has_no_via_imports(tmp_path):
    service = make_service(tmp_path, {
        "a.py": "def helper():\n    return 1\n\ndef run():\n    return helper()\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::run", "a.py::helper")
    assert edge.via_imports is None


def test_imports_edge_has_no_via_imports(tmp_path):
    service = make_service(tmp_path, {
        "producer.py": "def f():\n    return 1\n",
        "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.via_imports is None


def test_deleted_caller_derives_via_imports_from_base_imports(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "caller.py": "import helper\n\ndef gone():\n    return helper.do_work()\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
        {},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::gone", "helper.py::do_work")
    assert without_code(edge.via_imports) == [{"module": "helper", "status": "deleted"}]


def test_added_import_entry_carries_statement_as_add_code_line(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "caller.py": "def run():\n    return 1\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
        {
            "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    (entry,) = edge.via_imports
    (line,) = entry["code"]
    assert line["text"] == "import helper"
    assert line["op"] == "add"
    assert line["line"] == 1
    assert line["spans"]


def test_deleted_caller_import_entry_code_comes_from_base_statement(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "caller.py": "import helper\n\ndef gone():\n    return helper.do_work()\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
        {},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::gone", "helper.py::do_work")
    (entry,) = edge.via_imports
    (line,) = entry["code"]
    assert line["text"] == "import helper"
    assert line["op"] == "del"


def test_top_of_file_import_is_not_in_caller_code(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    (entry,) = edge.via_imports
    assert entry["in_caller_code"] is False


def test_import_nested_inside_caller_is_in_caller_code(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "def run():\n    import helper\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    (entry,) = edge.via_imports
    assert entry["in_caller_code"] is True


def test_deleted_caller_import_containment_resolves_in_base(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "caller.py": "def gone():\n    import helper\n    return helper.do_work()\n",
            "helper.py": "def do_work():\n    return 1\n",
        },
        {},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::gone", "helper.py::do_work")
    (entry,) = edge.via_imports
    assert entry["in_caller_code"] is True


def test_two_callers_in_the_same_file_each_pick_their_own_local_import(tmp_path):
    # Mirrors the agendabot dogfood shape (ticket 148): a module-level
    # import of the same module sits alongside two callers who each
    # locally re-import it under their own name-binding style — the
    # admitting entry for each caller must resolve to *that caller's own*
    # statement, not the module-level one and not the other caller's.
    service = make_service(tmp_path, {
        "caller.py": (
            "import helper\n"
            "\n"
            "def run_a():\n"
            "    import helper\n"
            "    return helper.do_work()\n"
            "\n"
            "def run_b():\n"
            "    from helper import do_work\n"
            "    return do_work()\n"
        ),
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    edge_a = edge_between(snapshot, "caller.py::run_a", "helper.py::do_work")
    (entry_a,) = edge_a.via_imports
    assert entry_a["in_caller_code"] is True
    (line_a,) = entry_a["code"]
    assert line_a["text"] == "import helper"
    assert line_a["line"] == 4

    edge_b = edge_between(snapshot, "caller.py::run_b", "helper.py::do_work")
    (entry_b,) = edge_b.via_imports
    assert entry_b["in_caller_code"] is True
    (line_b,) = entry_b["code"]
    assert line_b["text"] == "from helper import do_work"
    assert line_b["line"] == 8


def test_import_present_in_both_trees_renders_as_ctx_code_line(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    (entry,) = edge.via_imports
    (line,) = entry["code"]
    assert line["op"] == "ctx"


def test_imports_edge_status_stays_unchanged_even_when_endpoints_changed(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "producer.py": "def f():\n    return 1\n",
            "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
        },
        {
            "producer.py": "def f():\n    return 2\n",
            "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.status == Status.UNCHANGED


def test_imports_edge_for_added_import_has_added_status_and_module(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "producer.py": "def f():\n    return 1\n",
            "consumer.py": "def g():\n    return 1\n",
        },
        {
            "producer.py": "def f():\n    return 1\n",
            "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.status == Status.ADDED
    assert edge.module == "producer"


def test_imports_edge_for_removed_import_still_appears_with_deleted_status(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "producer.py": "def f():\n    return 1\n",
            "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
        },
        {
            "producer.py": "def f():\n    return 1\n",
            "consumer.py": "def g():\n    return 1\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.status == Status.DELETED
    assert edge.module == "producer"


def test_snapshot_assigns_layers_to_files_and_functions(tmp_path):
    service = make_service(tmp_path, {
        "pipeline.py": (
            "def load(path):\n"
            "    return path\n"
            "\n"
            "def parse(path):\n"
            "    return load(path)\n"
            "\n"
            "def report(path):\n"
            "    return parse(path)\n"
        ),
        "main.py": "import pipeline\n\ndef main():\n    return pipeline.report(\"x\")\n",
    })
    snapshot = service.snapshot()
    layers = {n.id: n.layer for n in snapshot.nodes}
    assert layers["main.py"] == 0
    assert layers["pipeline.py"] == 1
    assert layers["pipeline.py::report"] == 0
    assert layers["pipeline.py::parse"] == 1
    assert layers["pipeline.py::load"] == 2
    assert all("layer" in n.to_dict() for n in snapshot.nodes)


def test_ticket_linking_its_decision_adr_produces_an_implements_edge(tmp_path):
    service = make_service(tmp_path, {
        "docs/decisions/046-thing.md": "# 046. Thing\n\n## Decision\nbody\n",
        "docs/tickets/124-thing.md": (
            "# 124. Some ticket\n\nDecision: docs/decisions/046-thing.md\n"
        ),
    })
    snapshot = service.snapshot()
    edge = edge_between(
        snapshot, "docs/tickets/124-thing.md", "docs/decisions/046-thing.md", kind="implements")
    assert edge.status == Status.UNCHANGED
    assert not [
        e for e in snapshot.edges
        if e.kind == "references"
        and e.source == "docs/tickets/124-thing.md"
        and e.target == "docs/decisions/046-thing.md"
    ]


def test_implements_edge_added_status_reflects_new_decision_line(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {
            "docs/decisions/046-thing.md": "# 046. Thing\nbody\n",
            "docs/tickets/124-thing.md": "# 124. Ticket\nno link yet\n",
        },
        {
            "docs/decisions/046-thing.md": "# 046. Thing\nbody\n",
            "docs/tickets/124-thing.md": "# 124. Ticket\nDecision: docs/decisions/046-thing.md\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()
    edge = edge_between(
        snapshot, "docs/tickets/124-thing.md", "docs/decisions/046-thing.md", kind="implements")
    assert edge.status == Status.ADDED


def test_decision_ref_to_nonexistent_path_produces_no_edge(tmp_path):
    service = make_service(tmp_path, {
        "docs/tickets/124-thing.md": "# 124. Ticket\nDecision: docs/decisions/999-ghost.md\n",
    })
    snapshot = service.snapshot()
    assert not [e for e in snapshot.edges if e.kind == "implements"]
    assert not [e for e in snapshot.edges if e.kind == "references"]


def test_ticket_with_decision_line_and_inline_link_gets_both_edge_kinds(tmp_path):
    """ADR 065's core acceptance criterion: the ticket's ADR no longer
    appears in its `references` edges but does appear as an `implements`
    edge, while a plain inline link to some other doc still produces a
    `references` edge for that link."""
    service = make_service(tmp_path, {
        "docs/decisions/046-thing.md": "# 046. Thing\n\n## Decision\nbody\n",
        "docs/other.md": "# Other doc\n\nSome unrelated notes.\n",
        "docs/tickets/124-thing.md": (
            "# 124. Some ticket\n\nDecision: docs/decisions/046-thing.md\n\n"
            "See [other doc](../other.md) for background.\n"
        ),
    })
    snapshot = service.snapshot()

    implements_edge = edge_between(
        snapshot, "docs/tickets/124-thing.md", "docs/decisions/046-thing.md", kind="implements")
    assert implements_edge.status == Status.UNCHANGED

    reference_edge = edge_between(
        snapshot, "docs/tickets/124-thing.md", "docs/other.md", kind="references")
    assert reference_edge.status == Status.UNCHANGED

    assert not [
        e for e in snapshot.edges
        if e.kind == "references"
        and e.source == "docs/tickets/124-thing.md"
        and e.target == "docs/decisions/046-thing.md"
    ]


def test_adr_relationship_edges_carry_supersedes_amends_and_extends_kinds(tmp_path):
    service = make_service(tmp_path, {
        "docs/decisions/005-original-split.md": "# 005. Original split\n\nStatus: accepted\n",
        "docs/decisions/037-old-thing.md": "# 037. Old thing\n\nStatus: retired\n",
        "docs/decisions/041-extension.md": (
            "# 041. Extension\n\nStatus: accepted\nExtends: 005\n"
        ),
        "docs/decisions/058-new-thing.md": (
            "# 058. New thing\n\nStatus: accepted\nSupersedes: 037\n"
        ),
        "docs/decisions/061-amendment.md": (
            "# 061. Amendment\n\nStatus: accepted\nAmends: 058\n"
        ),
    })
    snapshot = service.snapshot()

    supersedes = edge_between(
        snapshot, "docs/decisions/058-new-thing.md", "docs/decisions/037-old-thing.md",
        kind="supersedes")
    assert supersedes.status == Status.UNCHANGED

    amends = edge_between(
        snapshot, "docs/decisions/061-amendment.md", "docs/decisions/058-new-thing.md",
        kind="amends")
    assert amends.status == Status.UNCHANGED

    extends = edge_between(
        snapshot, "docs/decisions/041-extension.md", "docs/decisions/005-original-split.md",
        kind="extends")
    assert extends.status == Status.UNCHANGED


def test_adr_relationship_edge_to_node_outside_snapshot_is_skipped(tmp_path):
    """Same defensive posture `_add_import_edges` already takes (ADR 065):
    an `adr_relationships` entry naming a target that isn't a node in the
    current snapshot produces no dangling edge. Built directly against
    `_add_adr_relationship_edges` with a hand-crafted `FileChange`, since
    the real `MarkdownExtractor` already refuses to record a relationship
    whose target doesn't resolve to a real file (tested in
    tests/indexing/test_markdown_extractor.py) — this test isolates
    `GraphService`'s own half of the defensive contract."""
    service = make_service(tmp_path, {
        "docs/decisions/058-new-thing.md": "# 058. New thing\n\nStatus: accepted\n",
    })
    snapshot = service.snapshot()

    ghost_index = FileIndex(
        rel_path="docs/decisions/058-new-thing.md",
        adr_relationships={"supersedes": {"docs/decisions/999-ghost.md"}},
    )
    change = FileChange(
        "docs/decisions/058-new-thing.md", Status.UNCHANGED, ghost_index, ghost_index, "",
    )
    service._add_adr_relationship_edges(snapshot, {"docs/decisions/058-new-thing.md": change})

    assert not [e for e in snapshot.edges if e.kind == "supersedes"]


def test_markdown_only_tree_produces_a_non_empty_graph(tmp_path):
    service = make_service(tmp_path, {"doc.md": "# Title\n\n## Section\nbody\n"})
    snapshot = service.snapshot()
    node_ids = {n.id for n in snapshot.nodes}
    assert "doc.md" in node_ids
    assert "doc.md::Section" in node_ids


def test_mixed_python_and_markdown_tree_renders_both(tmp_path):
    service = make_service(tmp_path, {
        "a.py": "def f():\n    pass\n",
        "doc.md": "# Title\n\n## Notes\nbody\n",
    })
    snapshot = service.snapshot()
    node_ids = {n.id for n in snapshot.nodes}
    assert "a.py" in node_ids
    assert "a.py::f" in node_ids
    assert "doc.md" in node_ids
    assert "doc.md::Notes" in node_ids


def test_mixed_tree_nodes_carry_domain_matching_their_extractor(tmp_path):
    service = make_service(tmp_path, {
        "a.py": "def f():\n    pass\n",
        "doc.md": "# Title\n\n## Notes\nbody\n",
    })
    nodes = {node.id: node for node in service.snapshot().nodes}
    assert nodes["a.py"].domain == "code"
    assert nodes["a.py::f"].domain == "code"
    assert nodes["doc.md"].domain == "doc"
    assert nodes["doc.md::Notes"].domain == "doc"


def test_state_hash_changes_when_a_markdown_heading_changes(tmp_path):
    repo, base_ref = make_repo(tmp_path, {"doc.md": "# Title\n\n## Section\nold body\n"})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    before = service.state_hash()

    (repo / "doc.md").write_text("# Title\n\n## Section\nnew body\n")

    assert service.state_hash() != before


def test_snapshot_file_nodes_report_their_top_level_directory_as_group(tmp_path):
    service = make_service(tmp_path, {
        "shop/checkout.py": "def pay():\n    pass\n",
        "shop/cart.py": "def add():\n    pass\n",
    })
    snapshot = service.snapshot()
    groups = {n.id: n.group for n in snapshot.nodes if n.kind == "file"}
    assert groups == {"shop/checkout.py": "shop", "shop/cart.py": "shop"}


def test_snapshot_file_nodes_skip_src_wrapper_directory_in_group(tmp_path):
    service = make_service(tmp_path, {
        "src/pkg/store.py": "def save():\n    pass\n",
        "src/pkg/webhook.py": "from pkg.store import save\n\ndef handle():\n    save()\n",
    })
    snapshot = service.snapshot()
    groups = {n.id: n.group for n in snapshot.nodes if n.kind == "file"}
    assert groups == {"src/pkg/store.py": "pkg", "src/pkg/webhook.py": "pkg"}


def spy_on_build_code_view(monkeypatch) -> list[tuple[str | None, str | None]]:
    """Records each (base_text, staged_text) pair build_code_view is called with."""
    import graphwerk.service as service_module

    calls: list[tuple[str | None, str | None]] = []
    original = service_module.build_code_view

    def wrapped(base_text, staged_text):
        calls.append((base_text, staged_text))
        return original(base_text, staged_text)

    monkeypatch.setattr(service_module, "build_code_view", wrapped)
    return calls


def test_second_snapshot_call_recomputes_no_code_views(tmp_path, monkeypatch):
    service = make_service(tmp_path, {
        "a.py": "def f():\n    return 1\n",
        "b.py": "def g():\n    return 1\n",
    })
    service.snapshot()

    calls = spy_on_build_code_view(monkeypatch)
    service.snapshot()

    assert calls == []


def test_touching_one_files_text_recomputes_only_its_code_views(tmp_path, monkeypatch):
    repo, base_ref = make_repo(
        tmp_path, {"a.py": "def f():\n    return 1\n", "b.py": "def g():\n    return 1\n"})
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    service.snapshot()

    write_tree(repo, {"a.py": "def f():\n    return 2\n"})
    calls = spy_on_build_code_view(monkeypatch)
    service.snapshot()

    assert ("def f():\n    return 1\n", "def f():\n    return 2\n") in calls
    assert not any("def g" in (base_text or "") or "def g" in (staged_text or "") for base_text, staged_text in calls)


def test_snapshot_flags_test_file_and_symbol_nodes_as_is_test(tmp_path):
    service = make_service(tmp_path, {
        "tests/test_x.py": "def test_one():\n    pass\n",
        "pkg/mod.py": "def helper():\n    pass\n",
    })
    nodes = service.snapshot().nodes
    flagged = {node.id for node in nodes if node.is_test}
    assert flagged == {"tests/test_x.py", "tests/test_x.py::test_one"}


def test_snapshot_sets_paired_file_and_excludes_paired_test_from_layering(tmp_path):
    service = make_service(tmp_path, {
        "x.py": "def f():\n    pass\n",
        "tests/test_x.py": "def test_f():\n    pass\n",
    })
    nodes = {node.id: node for node in service.snapshot().nodes}
    assert nodes["tests/test_x.py"].paired_file == "x.py"
    assert nodes["tests/test_x.py"].layer is None
    assert nodes["x.py"].paired_file is None
    assert nodes["x.py"].layer == 0


def test_snapshot_meta_carries_the_mined_commit_message(tmp_path):
    repo, base_ref = make_repo(
        tmp_path, {"a.py": "def f():\n    return 1\n"}, {"a.py": "def f():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(text_block(
            "- `a.py` (`f`): bumps the value because the request asked for it\n"
            "\n"
            "Commit-message: Bump f's return value"
        )),
    ])
    rationale = RationaleStore(staged_root=repo, transcript_path=transcript)
    service = GraphService(repo, base_ref, rationale)

    assert service.snapshot().meta["commit_message"] == "Bump f's return value"


def test_snapshot_meta_commit_message_is_null_without_the_line(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    pass\n"})
    meta = service.snapshot().meta
    assert "commit_message" in meta
    assert meta["commit_message"] is None


def test_changed_paths_returns_modified_and_added_but_not_unchanged(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {"modified.py": "def f():\n    return 1\n", "unchanged.py": "def g():\n    return 1\n"},
        {
            "modified.py": "def f():\n    return 2\n",
            "unchanged.py": "def g():\n    return 1\n",
            "added.py": "def h():\n    return 1\n",
        },
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))

    assert set(service.changed_paths()) == {"modified.py", "added.py"}


def test_uses_edge_from_added_function_to_unchanged_module_global(tmp_path):
    """Ticket 182: `uses` gets the same target-status filtering `calls`
    already has — an added caller resolves to an unchanged target and the
    edge takes the caller's own (added) status."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "_CACHE = {}\n"},
        {"a.py": "_CACHE = {}\n\ndef read():\n    return _CACHE\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::read", "a.py::_CACHE", kind="uses")
    assert edge.status == Status.ADDED


def test_uses_edge_for_class_attribute_resolves_within_same_class(tmp_path):
    """Same-file case always works (ADR 062): a method's `self.<attr>`
    reference resolves to its own class's variable symbol."""
    service = make_service(tmp_path, {
        "a.py": "class Config:\n    TIMEOUT = 5\n\n    def get(self):\n        return self.TIMEOUT\n",
    })
    snapshot = service.snapshot()

    assert ("a.py::Config.get", "a.py::Config.TIMEOUT") in uses_edge_pairs(snapshot)


def test_uses_edge_into_modified_global_has_modified_status(tmp_path):
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "_CACHE = {}\n\ndef read():\n    return _CACHE\n"},
        {"a.py": "_CACHE = {1: 2}\n\ndef read():\n    return _CACHE\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::read", "a.py::_CACHE", kind="uses")
    assert edge.status == Status.MODIFIED


def test_uses_edge_marks_unchanged_reader_affected_when_global_changes(tmp_path):
    """_mark_affected generalized to `edge.kind in {"calls", "uses"}`
    (ADR 062): an otherwise-unchanged reader of a changed global turns
    AFFECTED, the same blast-radius signal a caller of a changed function
    already gets."""
    repo, base_ref = make_repo(
        tmp_path,
        {"a.py": "_CACHE = {}\n\ndef read():\n    return _CACHE\n"},
        {"a.py": "_CACHE = {1: 2}\n\ndef read():\n    return _CACHE\n"},
    )
    service = GraphService(repo, base_ref, RationaleStore(staged_root=repo))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["a.py::read"].status == Status.AFFECTED


def test_uses_edge_does_not_resolve_to_same_named_global_in_unimported_file(tmp_path):
    """Phantom-edge guard (ADR 032/034), generalized to `uses`: a
    same-named module global in a file the reader never imports must not
    wire in just because the simple name matches."""
    service = make_service(tmp_path, {
        "a.py": "_CACHE = {}\n\ndef read():\n    return _CACHE\n",
        "b.py": "_CACHE = {}\n",
    })
    snapshot = service.snapshot()

    pairs = uses_edge_pairs(snapshot)
    assert ("a.py::read", "b.py::_CACHE") not in pairs
    assert ("a.py::read", "a.py::_CACHE") in pairs


def test_uses_edge_resolves_to_same_named_global_through_import_reachability(tmp_path):
    """Cross-file `uses` resolution reuses the exact same import-reachability
    functions `calls` edges already use (ADR 062) — no new resolution code,
    same function, exercised here through the same simple-name-collision
    mechanics the `calls` tests above already cover."""
    service = make_service(tmp_path, {
        "a.py": "import b\n\n_CACHE = {}\n\ndef read():\n    return _CACHE\n",
        "b.py": "_CACHE = {}\n",
    })
    snapshot = service.snapshot()

    assert ("a.py::read", "b.py::_CACHE") in uses_edge_pairs(snapshot)


def test_root_node_wires_to_every_layer_zero_entry_point(tmp_path):
    """Two files that don't import each other both sit at layer 0 (ADR
    022), so Root (ADR 063) converges on both of them."""
    service = make_service(tmp_path, {
        "a.py": "def f():\n    return 1\n",
        "b.py": "def g():\n    return 2\n",
    })
    snapshot = service.snapshot()

    root_nodes = [n for n in snapshot.nodes if n.kind == "root"]
    assert len(root_nodes) == 1
    root = root_nodes[0]
    assert root.id == "__root__"
    assert root.label == "Root"
    assert root.path == ""
    assert root.domain == "code"
    assert root.layer == -1
    assert root.order == 0

    entrypoint_targets = {e.target for e in snapshot.edges if e.kind == "entrypoint" and e.source == "__root__"}
    assert entrypoint_targets == {"a.py", "b.py"}


def test_root_node_absent_from_doc_only_tree(tmp_path):
    service = make_service(tmp_path, {"doc.md": "# Title\n\n## Section\nbody\n"})
    snapshot = service.snapshot()

    assert not any(n.kind == "root" for n in snapshot.nodes)
    assert not any(e.kind == "entrypoint" for e in snapshot.edges)


def test_root_node_carries_no_status_or_diff_and_serializes(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    snapshot = service.snapshot()

    root = next(n for n in snapshot.nodes if n.kind == "root")
    assert root.status == Status.UNCHANGED
    assert root.diff is None
    assert root.why is None
    assert root.code is None
    assert root.source is None

    payload = snapshot.to_dict()
    root_payload = next(n for n in payload["nodes"] if n["id"] == "__root__")
    assert root_payload["status"] == "unchanged"


def test_leaf_symbol_node_carries_used_import_statement(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": (
            "from fastapi import APIRouter\n"
            "\n"
            "class C:\n"
            "    def method(self):\n"
            "        return APIRouter()\n"
        ),
    })
    snapshot = service.snapshot()

    node = next(n for n in snapshot.nodes if n.id == "caller.py::C.method")
    (block,) = node.used_imports
    (line,) = block
    assert line["text"] == "from fastapi import APIRouter"
    assert line["line"] == 1
    assert line["op"] == "ctx"
    assert line["spans"]


def test_leaf_symbol_node_used_imports_is_none_when_nothing_used(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": "def f():\n    return 1\n",
    })
    snapshot = service.snapshot()

    node = next(n for n in snapshot.nodes if n.id == "caller.py::f")
    assert node.used_imports is None


def test_leaf_symbol_referencing_two_names_from_same_statement_renders_it_once(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": (
            "from typing import Any, Optional\n"
            "\n"
            "def f(x: Any) -> Optional[int]:\n"
            "    return x\n"
        ),
    })
    snapshot = service.snapshot()

    node = next(n for n in snapshot.nodes if n.id == "caller.py::f")
    assert len(node.used_imports) == 1


def test_leaf_symbol_used_imports_serializes_through_to_dict(tmp_path):
    service = make_service(tmp_path, {
        "caller.py": (
            "from fastapi import APIRouter\n"
            "\n"
            "def f():\n"
            "    return APIRouter()\n"
        ),
    })
    snapshot = service.snapshot()

    payload = snapshot.to_dict()
    node_payload = next(n for n in payload["nodes"] if n["id"] == "caller.py::f")
    (block,) = node_payload["used_imports"]
    (line,) = block
    assert line["text"] == "from fastapi import APIRouter"
