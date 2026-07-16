from pathlib import Path

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


def make_service(tmp_path: Path, files: dict[str, str]) -> GraphService:
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, files)
    write_tree(staged, files)
    return GraphService(base, staged, RationaleStore(staged_root=staged))


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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    nodes = {n.id: n for n in service.snapshot().nodes}
    assert nodes["a.py::f"].source == "def f():\n    return 2\n"


def test_deleted_symbol_carries_base_source(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def gone():\n    return 1\n\ndef kept():\n    pass\n"})
    write_tree(staged, {"a.py": "def kept():\n    pass\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
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
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def f():\n    return 1\n"})
    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged))

    message = service.snapshot().meta["rationale"]["message"]
    assert message is not None
    assert str(staged) in message


def test_calls_edge_into_modified_target_has_modified_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def target():\n    return 1\n\ndef caller():\n    return target()\n"})
    write_tree(staged, {"a.py": "def target():\n    return 2\n\ndef caller():\n    return target()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::target")
    assert edge.status == Status.MODIFIED


def test_calls_edge_into_added_target_has_added_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def caller():\n    return 1\n"})
    write_tree(staged, {"a.py": "def caller():\n    return new_func()\n\ndef new_func():\n    return 2\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::new_func")
    assert edge.status == Status.ADDED


def test_calls_edge_into_deleted_target_has_deleted_status(tmp_path):
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def gone():\n    return 1\n\ndef caller():\n    return gone()\n"})
    write_tree(staged, {"a.py": "def caller():\n    return gone()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::caller", "a.py::gone")
    assert edge.status == Status.DELETED


def test_calls_edge_that_causes_affected_status_keeps_targets_own_status(tmp_path):
    """The edge _mark_affected used to flip its source to AFFECTED still
    reports the target's real status, not "affected" — target status wins."""
    base = tmp_path / "base"
    staged = tmp_path / "staged"
    write_tree(base, {"a.py": "def target():\n    return 1\n\ndef caller():\n    return target()\n"})
    write_tree(staged, {"a.py": "def target():\n    return 2\n\ndef caller():\n    return target()\n"})
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "a.py::runner", "a.py::helper")
    assert edge.status == Status.UNCHANGED


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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    snapshot = service.snapshot()

    edge = edge_between(snapshot, "consumer.py", "producer.py", kind="imports")
    assert edge.status == Status.UNCHANGED


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
    assert layers["pipeline.py"] == 0
    assert layers["main.py"] == 1
    assert layers["pipeline.py::load"] == 0
    assert layers["pipeline.py::parse"] == 1
    assert layers["pipeline.py::report"] == 2
    assert all("layer" in n.to_dict() for n in snapshot.nodes)


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
    service = GraphService(base, staged, RationaleStore(staged_root=staged))
    service.snapshot()

    write_tree(staged, {"a.py": "def f():\n    return 2\n"})
    calls = spy_on_build_code_view(monkeypatch)
    service.snapshot()

    assert ("def f():\n    return 1\n", "def f():\n    return 2\n") in calls
    assert not any("def g" in (base_text or "") or "def g" in (staged_text or "") for base_text, staged_text in calls)
