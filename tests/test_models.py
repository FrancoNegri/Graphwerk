from graphwerk.models import GraphNode, Snapshot


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


