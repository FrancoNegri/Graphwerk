from graphwerk.layout import assign_layers
from graphwerk.models import GraphEdge, GraphNode


def file_node(rel: str) -> GraphNode:
    return GraphNode(id=rel, label=rel, kind="file", path=rel)


def function_node(rel: str, name: str) -> GraphNode:
    return GraphNode(id=f"{rel}::{name}", label=name, kind="function", path=rel, parent=rel)


def class_node(rel: str, name: str) -> GraphNode:
    return GraphNode(id=f"{rel}::{name}", label=name, kind="class", path=rel, parent=rel)


def method_node(rel: str, qualname: str) -> GraphNode:
    class_name = qualname.split(".")[0]
    return GraphNode(
        id=f"{rel}::{qualname}",
        label=qualname.split(".")[-1],
        kind="method",
        path=rel,
        parent=f"{rel}::{class_name}",
    )


def imports(source_rel: str, target_rel: str) -> GraphEdge:
    return GraphEdge(source_rel, target_rel, "imports")


def calls(source_id: str, target_id: str) -> GraphEdge:
    return GraphEdge(source_id, target_id, "calls")


def layers_of(nodes: list[GraphNode]) -> dict[str, int | None]:
    return {node.id: node.layer for node in nodes}


def test_files_layered_by_import_depth():
    nodes = [file_node("a.py"), file_node("b.py"), file_node("c.py")]
    edges = [imports("a.py", "b.py"), imports("b.py", "c.py")]
    assign_layers(nodes, edges)
    assert layers_of(nodes) == {"c.py": 0, "b.py": 1, "a.py": 2}


def test_file_importing_nothing_is_layer_zero():
    nodes = [file_node("lonely.py")]
    assign_layers(nodes, [])
    assert nodes[0].layer == 0


def test_diamond_import_takes_longest_path():
    nodes = [file_node(rel) for rel in ("a.py", "b.py", "c.py", "d.py")]
    edges = [
        imports("a.py", "b.py"),
        imports("b.py", "c.py"),
        imports("c.py", "d.py"),
        imports("a.py", "d.py"),
    ]
    assign_layers(nodes, edges)
    assert layers_of(nodes)["a.py"] == 3


def test_import_cycle_collapses_into_one_shared_layer():
    nodes = [file_node(rel) for rel in ("x.py", "y.py", "base.py")]
    edges = [
        imports("x.py", "y.py"),
        imports("y.py", "x.py"),
        imports("y.py", "base.py"),
    ]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["x.py"] == layers["y.py"] == 1
    assert layers["base.py"] == 0


def test_functions_layered_by_intra_file_call_depth():
    nodes = [
        file_node("flow.py"),
        function_node("flow.py", "top"),
        function_node("flow.py", "middle"),
        function_node("flow.py", "leaf"),
    ]
    edges = [
        calls("flow.py::top", "flow.py::middle"),
        calls("flow.py::middle", "flow.py::leaf"),
    ]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["flow.py::leaf"] == 0
    assert layers["flow.py::middle"] == 1
    assert layers["flow.py::top"] == 2


def test_cross_file_calls_do_not_affect_symbol_layers():
    nodes = [
        file_node("flow.py"),
        function_node("flow.py", "caller"),
        file_node("other.py"),
        function_node("other.py", "helper"),
    ]
    edges = [calls("flow.py::caller", "other.py::helper")]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["flow.py::caller"] == 0
    assert layers["other.py::helper"] == 0


def test_mutual_recursion_shares_a_layer_and_caller_sits_above():
    nodes = [
        file_node("rec.py"),
        function_node("rec.py", "ping"),
        function_node("rec.py", "pong"),
        function_node("rec.py", "driver"),
    ]
    edges = [
        calls("rec.py::ping", "rec.py::pong"),
        calls("rec.py::pong", "rec.py::ping"),
        calls("rec.py::driver", "rec.py::ping"),
    ]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["rec.py::ping"] == layers["rec.py::pong"] == 0
    assert layers["rec.py::driver"] == 1


def test_self_recursion_gets_a_layer_without_crashing():
    nodes = [file_node("rec.py"), function_node("rec.py", "solo")]
    edges = [calls("rec.py::solo", "rec.py::solo")]
    assign_layers(nodes, edges)
    assert layers_of(nodes)["rec.py::solo"] == 0


def test_functions_without_calls_all_land_in_layer_zero():
    nodes = [
        file_node("utils.py"),
        function_node("utils.py", "format_price"),
        function_node("utils.py", "deprecated_helper"),
    ]
    assign_layers(nodes, [])
    layers = layers_of(nodes)
    assert layers["utils.py::format_price"] == 0
    assert layers["utils.py::deprecated_helper"] == 0


def test_classes_and_methods_get_no_layer():
    nodes = [
        file_node("svc.py"),
        class_node("svc.py", "Service"),
        method_node("svc.py", "Service.run"),
        method_node("svc.py", "Service.helper"),
    ]
    edges = [calls("svc.py::Service.run", "svc.py::Service.helper")]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["svc.py::Service"] is None
    assert layers["svc.py::Service.run"] is None
    assert layers["svc.py::Service.helper"] is None


def test_node_to_dict_carries_layer():
    node = file_node("a.py")
    assert node.to_dict()["layer"] is None
    node.layer = 2
    assert node.to_dict()["layer"] == 2
