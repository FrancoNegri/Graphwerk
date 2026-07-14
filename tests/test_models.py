from graphwerk.models import GraphNode


def test_graph_node_source_defaults_to_none_and_is_serialized():
    node = GraphNode(id="a.py", label="a.py", kind="file", path="a.py")
    assert node.source is None
    assert node.to_dict()["source"] is None


def test_graph_node_source_round_trips_through_to_dict():
    node = GraphNode(
        id="a.py::f", label="f", kind="function", path="a.py", source="def f():\n    pass\n"
    )
    assert node.to_dict()["source"] == "def f():\n    pass\n"
