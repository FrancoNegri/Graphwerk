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
