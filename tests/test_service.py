import json
from pathlib import Path

from graphwerk.approval import ApprovalStore
from graphwerk.models import Status
from graphwerk.rationale import RationaleStore
from graphwerk.service import GraphService, ModuleFileResolver


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def import_edges(snapshot) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in snapshot.edges if e.kind == "imports"}


def edge_between(snapshot, source: str, target: str, kind: str = "calls"):
    for edge in snapshot.edges:
        if edge.source == source and edge.target == target and edge.kind == kind:
            return edge
    raise AssertionError(f"no {kind} edge {source} -> {target}")


def without_code(via_imports: list) -> list:
    return [{key: entry[key] for key in ("module", "status")} for entry in via_imports]


def make_service(tmp_path: Path, files: dict[str, str],
                 approval_store: ApprovalStore | None = None) -> GraphService:
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, files)
    write_tree(staged, files)
    return GraphService(base, staged, RationaleStore(staged_root=staged), approval_store or ApprovalStore(staged))


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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py::f"].source == "def f():\n    return 2\n"


def test_deleted_symbol_carries_base_source(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def gone():\n    return 1\n\ndef kept():\n    pass\n"})
    write_tree(staged, {"a.py": "def kept():\n    pass\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py::gone"].source == "def gone():\n    return 1\n"


def test_file_nodes_carry_full_source_text(tmp_path):
    text = "def f():\n    pass\n"
    service = make_service(tmp_path, {"a.py": text})
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py"].source == text


def test_modified_symbol_code_interleaves_del_lines_with_spans(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    write_tree(staged, {"new.py": "def f():\n    return 1\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    for node_id in ("new.py", "new.py::f"):
        code = nodes[node_id].code
        assert code
        assert all(line["op"] == "add" for line in code)


def test_deleted_file_nodes_code_is_all_removed(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"old.py": "def f():\n    return 1\n"})
    staged.mkdir()
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    for node_id in ("old.py", "old.py::f"):
        code = nodes[node_id].code
        assert code
        assert all(line["op"] == "del" for line in code)


def test_unreadable_file_node_code_is_none(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    base.mkdir()
    staged.mkdir()
    (base / "junk.py").write_bytes(b"\xff\xfe not utf-8 \xff")
    (staged / "junk.py").write_bytes(b"\xff\xfe still not utf-8 \xff")
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["junk.py"].code is None


def test_snapshot_marks_file_node_approved_from_approval_store(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    approval_store = ApprovalStore(staged)
    approval_store.approve("a.py")
    service = GraphService(base, staged, RationaleStore(staged_root=staged), approval_store)

    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py"].approved is True


def test_snapshot_unapproved_file_node_is_not_approved(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))

    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py"].approved is False


def test_snapshot_symbol_node_is_never_approved(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    approval_store = ApprovalStore(staged)
    approval_store.approve("a.py")
    service = GraphService(base, staged, RationaleStore(staged_root=staged), approval_store)

    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py::f"].approved is False


def test_snapshot_approval_evaporates_after_the_staged_file_changes(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    approval_store = ApprovalStore(staged)
    approval_store.approve("a.py")
    service = GraphService(base, staged, RationaleStore(staged_root=staged), approval_store)
    assert service.snapshot().nodes[0].approved is True

    (staged / "a.py").write_text("def f():\n    return 3\n" * 50)

    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py"].approved is False


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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))

    message = service.snapshot().meta["rationale"]["message"]
    assert message is not None
    assert str(staged) in message


def write_transcript(path: Path, entries: list) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def assistant_entry(*blocks) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def edit_block(file_path: Path) -> dict:
    return {"type": "tool_use", "name": "Edit", "input": {"file_path": str(file_path)}}


def test_snapshot_marks_low_confidence_why_from_proximity_fallback(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"business.py": "def core():\n    return 1\n", "deps.py": "def helper():\n    return 1\n"})
    write_tree(staged, {"business.py": "def core():\n    return 2\n", "deps.py": "def helper():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Now building the business logic module."),
            edit_block(staged / "business.py"),
            edit_block(staged / "deps.py"),
        ),
        assistant_entry(text_block("Final: `business.py` implements the core rules.")),
    ])
    rationale = RationaleStore(staged_root=staged, transcript_path=transcript)
    service = GraphService(base, staged, rationale, ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["business.py"].why_confident is True
    assert nodes["deps.py"].why_confident is False


def test_snapshot_symbol_node_carries_why_confidence(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"business.py": "def core():\n    return 1\n"})
    write_tree(staged, {"business.py": "def core():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Working on it."),
            edit_block(staged / "business.py"),
        ),
        assistant_entry(text_block("Final: `core` now returns the updated value.")),
    ])
    rationale = RationaleStore(staged_root=staged, transcript_path=transcript)
    service = GraphService(base, staged, rationale, ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["business.py::core"].why_confident is True


def test_unchanged_node_has_no_why_confidence(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py"].why_confident is None


def test_snapshot_marks_describes_only_why_from_a_guidance_bullet(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"deps.py": "def helper():\n    return 1\n"})
    write_tree(staged, {"deps.py": "def helper():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Working on it."),
            edit_block(staged / "deps.py"),
        ),
        assistant_entry(text_block("- `deps.py`: FastAPI dependency-injection providers.")),
    ])
    rationale = RationaleStore(staged_root=staged, transcript_path=transcript)
    service = GraphService(base, staged, rationale, ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["deps.py"].why_justifies is False


def test_snapshot_marks_justifying_why_from_a_guidance_bullet(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"flags.py": "def helper():\n    return 1\n"})
    write_tree(staged, {"flags.py": "def helper():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(
            text_block("Working on it."),
            edit_block(staged / "flags.py"),
        ),
        assistant_entry(text_block(
            "- `flags.py`: shared env-derived flags, split out since several "
            "other modules need them."
        )),
    ])
    rationale = RationaleStore(staged_root=staged, transcript_path=transcript)
    service = GraphService(base, staged, rationale, ApprovalStore(staged))
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["flags.py"].why_justifies is True


def test_unchanged_node_has_no_why_justifies(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    return 1\n"})
    nodes = {n.id: n for n in service.snapshot().nodes}

    assert nodes["a.py"].why_justifies is None


def test_calls_edge_into_modified_target_has_modified_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def target():\n    return 1\n\ndef caller():\n    return target()\n"})
    write_tree(staged, {"a.py": "def target():\n    return 2\n\ndef caller():\n    return target()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::target")
    assert edge.status == Status.MODIFIED


def test_calls_edge_into_added_target_has_added_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def caller():\n    return 1\n"})
    write_tree(staged, {"a.py": "def caller():\n    return new_func()\n\ndef new_func():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::new_func")
    assert edge.status == Status.ADDED


def calls_edge_pairs(snapshot) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in snapshot.edges if e.kind == "calls"}


def test_unchanged_caller_does_not_resolve_to_deleted_target_it_no_longer_calls(tmp_path):
    """Mirror phantom case (ADR 032): a caller whose calls came from
    staged_info must not resolve to a deleted (base-only) target it never
    actually called in the staged tree, even if the name still matches."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def gone():\n    return 1\n\ndef caller():\n    return gone()\n"})
    write_tree(staged, {"a.py": "def caller():\n    return gone()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    assert ("a.py::caller", "a.py::gone") not in calls_edge_pairs(snapshot)


def test_unchanged_caller_does_not_resolve_to_deleted_target_in_another_file(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "a.py": "def caller():\n    return helper()\n",
        "b.py": "def helper():\n    return 1\n",
    })
    write_tree(staged, {"a.py": "def caller():\n    return helper()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    assert ("a.py::caller", "b.py::helper") not in calls_edge_pairs(snapshot)


def test_deleted_caller_does_not_resolve_to_added_target_with_same_name(tmp_path):
    """Phantom case (ADR 032): a deleted (base-only) caller must not resolve
    to an added (staged-only) target that only exists in the other tree,
    e.g. a relocated symbol's old and new copies sharing a simple name."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def gone():\n    return helper()\n"})
    write_tree(staged, {"b.py": "def helper():\n    return 1\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    assert ("a.py::gone", "b.py::helper") not in calls_edge_pairs(snapshot)


def test_deleted_caller_still_resolves_to_deleted_target_it_actually_called(tmp_path):
    """Regression guard (ADR 032): the deleted -> deleted pairing that
    reconstructs a gutted file's real internal wiring stays intact."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def helper():\n    return 1\n\ndef gone():\n    return helper()\n"})
    staged.mkdir()
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::gone", "a.py::helper")
    assert edge.status == Status.DELETED


def test_calls_edge_that_causes_affected_status_keeps_targets_own_status(tmp_path):
    """The edge _mark_affected used to flip its source to AFFECTED still
    reports the target's real status, not "affected" — target status wins."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def target():\n    return 1\n\ndef caller():\n    return target()\n"})
    write_tree(staged, {"a.py": "def target():\n    return 2\n\ndef caller():\n    return target()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    nodes = {n.id: n for n in snapshot.nodes}
    assert nodes["a.py::caller"].status == Status.AFFECTED
    edge = edge_between(snapshot, "a.py::caller", "a.py::target")
    assert edge.status == Status.MODIFIED


def test_calls_edge_to_unrelated_unchanged_target_has_unchanged_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "a.py": "def helper():\n    return 1\n\ndef runner():\n    return helper()\n",
        "b.py": "def other():\n    return 1\n",
    })
    write_tree(staged, {
        "a.py": "def helper():\n    return 1\n\ndef runner():\n    return helper()\n",
        "b.py": "def other():\n    return 2\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::runner", "a.py::helper")
    assert edge.status == Status.UNCHANGED


def test_calls_edge_to_unrelated_target_from_affected_source_has_unchanged_status(tmp_path):
    """A caller becomes AFFECTED via its call to a modified target; a
    different, unrelated call it also makes must not borrow that label —
    only the call that actually leads into changed code should."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "a.py": (
            "def target():\n    return 1\n\n"
            "def unrelated():\n    return 1\n\n"
            "def caller():\n    target()\n    return unrelated()\n"
        ),
    })
    write_tree(staged, {
        "a.py": (
            "def target():\n    return 2\n\n"
            "def unrelated():\n    return 1\n\n"
            "def caller():\n    target()\n    return unrelated()\n"
        ),
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "pkg/__init__.py": "from pkg.inner import Thing\n",
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from pkg import Thing\n\ndef gone():\n    return Thing()\n",
    })
    staged.mkdir()
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    assert ("caller.py::gone", "pkg/inner.py::Thing") in calls_edge_pairs(snapshot)


def test_unchanged_caller_does_not_resolve_transitively_through_base_only_hop(tmp_path):
    """Mirror of ADR 032 tree containment on the new traversal: the
    intermediate re-export file existed in base but was removed in staged,
    so a caller whose calls come from the staged tree must not resolve
    through it even though the resolver can still map the module name to
    that path."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "pkg/__init__.py": "from pkg.inner import Thing\n",
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
    })
    write_tree(staged, {
        "pkg/inner.py": "class Thing:\n    pass\n",
        "caller.py": "from pkg import Thing\n\ndef run():\n    return Thing()\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "caller.py": "def run():\n    return 1\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    write_tree(staged, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "caller.py": "import helper\n\ndef gone():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    staged.mkdir()
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::gone", "helper.py::do_work")
    assert without_code(edge.via_imports) == [{"module": "helper", "status": "deleted"}]


def test_added_import_entry_carries_statement_as_add_code_line(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "caller.py": "def run():\n    return 1\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    write_tree(staged, {
        "caller.py": "import helper\n\ndef run():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::run", "helper.py::do_work")
    (entry,) = edge.via_imports
    (line,) = entry["code"]
    assert line["text"] == "import helper"
    assert line["op"] == "add"
    assert line["line"] == 1
    assert line["spans"]


def test_deleted_caller_import_entry_code_comes_from_base_statement(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "caller.py": "import helper\n\ndef gone():\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    staged.mkdir()
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "caller.py": "def gone():\n    import helper\n    return helper.do_work()\n",
        "helper.py": "def do_work():\n    return 1\n",
    })
    staged.mkdir()
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "caller.py::gone", "helper.py::do_work")
    (entry,) = edge.via_imports
    assert entry["in_caller_code"] is True


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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "producer.py": "def f():\n    return 1\n",
        "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
    })
    write_tree(staged, {
        "producer.py": "def f():\n    return 2\n",
        "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.status == Status.UNCHANGED


def test_imports_edge_for_added_import_has_added_status_and_module(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "producer.py": "def f():\n    return 1\n",
        "consumer.py": "def g():\n    return 1\n",
    })
    write_tree(staged, {
        "producer.py": "def f():\n    return 1\n",
        "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.status == Status.ADDED
    assert edge.module == "producer"


def test_imports_edge_for_removed_import_still_appears_with_deleted_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "producer.py": "def f():\n    return 1\n",
        "consumer.py": "import producer\n\ndef g():\n    return producer.f()\n",
    })
    write_tree(staged, {
        "producer.py": "def f():\n    return 1\n",
        "consumer.py": "def g():\n    return 1\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
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


def test_ticket_linking_its_decision_adr_produces_a_references_edge(tmp_path):
    service = make_service(tmp_path, {
        "docs/decisions/046-thing.md": "# 046. Thing\n\n## Decision\nbody\n",
        "docs/tickets/124-thing.md": (
            "# 124. Some ticket\n\nDecision: docs/decisions/046-thing.md\n"
        ),
    })
    snapshot = service.snapshot()
    edge = edge_between(
        snapshot, "docs/tickets/124-thing.md", "docs/decisions/046-thing.md", kind="references")
    assert edge.status == Status.UNCHANGED


def test_reference_edge_added_status_reflects_new_link(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {
        "docs/decisions/046-thing.md": "# 046. Thing\nbody\n",
        "docs/tickets/124-thing.md": "# 124. Ticket\nno link yet\n",
    })
    write_tree(staged, {
        "docs/decisions/046-thing.md": "# 046. Thing\nbody\n",
        "docs/tickets/124-thing.md": "# 124. Ticket\nDecision: docs/decisions/046-thing.md\n",
    })
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    snapshot = service.snapshot()
    edge = edge_between(
        snapshot, "docs/tickets/124-thing.md", "docs/decisions/046-thing.md", kind="references")
    assert edge.status == Status.ADDED


def test_reference_to_nonexistent_path_produces_no_edge(tmp_path):
    service = make_service(tmp_path, {
        "docs/tickets/124-thing.md": "# 124. Ticket\nDecision: docs/decisions/999-ghost.md\n",
    })
    snapshot = service.snapshot()
    assert not [e for e in snapshot.edges if e.kind == "references"]


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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"doc.md": "# Title\n\n## Section\nold body\n"})
    write_tree(staged, {"doc.md": "# Title\n\n## Section\nold body\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    before = service.state_hash()

    (staged / "doc.md").write_text("# Title\n\n## Section\nnew body\n")

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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n", "b.py": "def g():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 1\n", "b.py": "def g():\n    return 1\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged), ApprovalStore(staged))
    service.snapshot()

    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})

    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, [
        assistant_entry(text_block(
            "- `a.py` (`f`): bumps the value because the request asked for it\n"
            "\n"
            "Commit-message: Bump f's return value"
        )),
    ])
    rationale = RationaleStore(staged_root=staged, transcript_path=transcript)
    service = GraphService(base, staged, rationale, ApprovalStore(staged))

    assert service.snapshot().meta["commit_message"] == "Bump f's return value"


def test_snapshot_meta_commit_message_is_null_without_the_line(tmp_path):
    service = make_service(tmp_path, {"a.py": "def f():\n    pass\n"})
    meta = service.snapshot().meta
    assert "commit_message" in meta
    assert meta["commit_message"] is None
