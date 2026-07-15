from graphwerk.models import GraphNode


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


