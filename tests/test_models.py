from graphwerk.models import GraphEdge, GraphNode, Snapshot


def test_graph_node_source_stays_internal_and_off_the_wire():
    node = GraphNode(
        id="a.py::f", label="f", kind="function", path="a.py", source="def f():\n    pass\n"
    )
    assert node.source == "def f():\n    pass\n"
    assert "source" not in node.to_dict()


def test_graph_node_code_defaults_to_none_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.code is None
    assert node.to_dict()["code"] is None


def test_graph_node_code_round_trips_through_to_dict():
    view = [{"text": "x = 1", "op": "ctx", "line": 1, "spans": []}]
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py", code=view)
    assert node.to_dict()["code"] == view


def test_snapshot_meta_defaults_empty_and_is_serialized():
    assert Snapshot().to_dict()["meta"] == {}
    snapshot = Snapshot(meta={"rationale": {"sidecar_entries": 3}})
    assert snapshot.to_dict()["meta"] == {"rationale": {"sidecar_entries": 3}}


def test_graph_node_order_defaults_to_none_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.order is None
    assert node.to_dict()["order"] is None
    node.order = 3
    assert node.to_dict()["order"] == 3


def test_graph_node_group_defaults_to_none_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.group is None
    assert node.to_dict()["group"] is None
    node.group = "src"
    assert node.to_dict()["group"] == "src"


def test_graph_node_why_confident_defaults_to_none_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.why_confident is None
    assert node.to_dict()["why_confident"] is None
    node.why_confident = False
    assert node.to_dict()["why_confident"] is False


def test_graph_node_why_justifies_defaults_to_none_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.why_justifies is None
    assert node.to_dict()["why_justifies"] is None
    node.why_justifies = False
    assert node.to_dict()["why_justifies"] is False


def test_graph_node_is_test_omitted_from_dict_unless_true():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.is_test is False
    assert "is_test" not in node.to_dict()
    node.is_test = True
    assert node.to_dict()["is_test"] is True


def test_graph_node_paired_file_omitted_from_dict_unless_set():
    node = GraphNode(id="tests/test_a.py", label="tests/test_a.py", kind="file", path="tests/test_a.py")
    assert node.paired_file is None
    assert "paired_file" not in node.to_dict()
    node.paired_file = "a.py"
    assert node.to_dict()["paired_file"] == "a.py"


def test_graph_node_approved_defaults_to_false_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.approved is False
    assert node.to_dict()["approved"] is False
    node.approved = True
    assert node.to_dict()["approved"] is True


def test_graph_edge_via_imports_defaults_to_none_and_is_serialized():
    edge = GraphEdge(source="a.py::f", target="b.py::g", kind="calls")
    assert edge.via_imports is None
    assert edge.to_dict()["via_imports"] is None
    edge.via_imports = [{"module": "b", "status": "added"}]
    assert edge.to_dict()["via_imports"] == [{"module": "b", "status": "added"}]
