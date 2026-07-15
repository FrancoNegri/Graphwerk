from pathlib import Path

from graphwerk.rationale import RationaleStore
from graphwerk.service import GraphService, ModuleFileResolver


def write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, source in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)


def import_edges(snapshot) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in snapshot.edges if e.kind == "imports"}


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
