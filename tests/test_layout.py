from graphwerk.layout import (
    _grouped_by_directory,
    is_test_path,
    _orders_by_barycenter,
    assign_layers,
    group_for_path,
)
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
    assert layers_of(nodes) == {"a.py": 0, "b.py": 1, "c.py": 2}


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
    layers = layers_of(nodes)
    assert layers["a.py"] == 0
    assert layers["d.py"] == 3


def test_unrelated_entry_points_land_at_layer_zero_despite_differing_depths():
    nodes = [file_node(rel) for rel in ("shallow_entry.py", "deep_entry.py", "mid.py", "leaf.py")]
    edges = [
        imports("shallow_entry.py", "leaf.py"),
        imports("deep_entry.py", "mid.py"),
        imports("mid.py", "leaf.py"),
    ]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["shallow_entry.py"] == 0
    assert layers["deep_entry.py"] == 0


def test_import_cycle_collapses_into_one_shared_layer():
    nodes = [file_node(rel) for rel in ("x.py", "y.py", "base.py")]
    edges = [
        imports("x.py", "y.py"),
        imports("y.py", "x.py"),
        imports("y.py", "base.py"),
    ]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["x.py"] == layers["y.py"] == 0
    assert layers["base.py"] == 1


def test_import_chain_through_noise_filtered_file_keeps_true_depth():
    nodes = [file_node("a.py"), file_node("c.py")]
    edges = [imports("a.py", "b.py"), imports("b.py", "c.py")]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["a.py"] == 0
    assert layers["c.py"] == 2


def test_import_from_test_file_does_not_demote_the_importee():
    nodes = [file_node("app.py"), file_node("tests/test_app.py")]
    edges = [imports("tests/test_app.py", "app.py")]
    assign_layers(nodes, edges)
    layers = layers_of(nodes)
    assert layers["app.py"] == 0
    assert layers["tests/test_app.py"] == 0


def testis_test_path_matches_tests_segment_or_test_filename():
    assert is_test_path("tests/foo.py")
    assert is_test_path("pkg/test_bar.py")
    assert not is_test_path("pkg/app.py")


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
    assert layers["flow.py::top"] == 0
    assert layers["flow.py::middle"] == 1
    assert layers["flow.py::leaf"] == 2


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
    assert layers["rec.py::driver"] == 0
    assert layers["rec.py::ping"] == layers["rec.py::pong"] == 1


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


def orders_of(nodes: list[GraphNode]) -> dict[str, int | None]:
    return {node.id: node.order for node in nodes}


def test_imported_neighbors_get_nearby_orders_and_unrelated_file_stays_aside():
    nodes = [
        file_node("alpha.py"),
        file_node("beta.py"),
        file_node("m_uses_beta.py"),
        file_node("n_uses_alpha.py"),
        file_node("unrelated.py"),
    ]
    edges = [
        imports("m_uses_beta.py", "beta.py"),
        imports("n_uses_alpha.py", "alpha.py"),
    ]
    assign_layers(nodes, edges)
    orders = orders_of(nodes)
    assert orders["m_uses_beta.py"] == orders["beta.py"] == 0
    assert orders["n_uses_alpha.py"] == orders["alpha.py"] == 1
    assert orders["unrelated.py"] == 2


def test_functions_are_ordered_within_their_own_file_only():
    nodes = [
        file_node("solo.py"),
        function_node("solo.py", "top"),
        function_node("solo.py", "leaf"),
        file_node("utils.py"),
        function_node("utils.py", "aaa_helper"),
        function_node("utils.py", "zzz_helper"),
    ]
    edges = [calls("solo.py::top", "solo.py::leaf")]
    assign_layers(nodes, edges)
    orders = orders_of(nodes)
    assert orders["solo.py::top"] == 0
    assert orders["solo.py::leaf"] == 0
    assert orders["utils.py::aaa_helper"] == 0
    assert orders["utils.py::zzz_helper"] == 1


def test_classes_and_methods_get_no_order():
    nodes = [
        file_node("svc.py"),
        class_node("svc.py", "Service"),
        method_node("svc.py", "Service.run"),
    ]
    assign_layers(nodes, [])
    orders = orders_of(nodes)
    assert orders["svc.py"] == 0
    assert orders["svc.py::Service"] is None
    assert orders["svc.py::Service.run"] is None


def test_barycenter_uncrosses_a_two_layer_crossing():
    layer_by_id = {"a.py": 0, "b.py": 0, "c.py": 1, "d.py": 1}
    neighbors_of = {"c.py": {"b.py"}, "d.py": {"a.py"}}
    orders = _orders_by_barycenter(layer_by_id, neighbors_of)
    assert orders == {"a.py": 0, "b.py": 1, "d.py": 0, "c.py": 1}


def test_node_without_cross_layer_neighbors_keeps_its_slot():
    layer_by_id = {"a": 0, "b": 0, "c": 0, "p": 1, "q": 1, "r": 1}
    neighbors_of = {"p": {"c"}, "r": {"a"}}
    orders = _orders_by_barycenter(layer_by_id, neighbors_of)
    assert orders == {"a": 0, "b": 1, "c": 2, "r": 0, "q": 1, "p": 2}


def test_barycenter_is_deterministic_across_runs():
    layer_by_id = {"a.py": 0, "b.py": 0, "c.py": 1, "d.py": 1}
    neighbors_of = {"c.py": {"b.py"}, "d.py": {"a.py"}}
    first = _orders_by_barycenter(layer_by_id, neighbors_of)
    second = _orders_by_barycenter(dict(layer_by_id), {k: set(v) for k, v in neighbors_of.items()})
    assert first == second


def test_single_layer_keeps_stable_initial_id_order():
    layer_by_id = {"beta": 0, "alpha": 0, "gamma": 0}
    orders = _orders_by_barycenter(layer_by_id, {"beta": {"alpha"}})
    assert orders == {"alpha": 0, "beta": 1, "gamma": 2}


def test_edge_spanning_two_layers_uses_neighbor_position_in_its_own_layer():
    layer_by_id = {"a": 0, "b": 0, "m": 1, "p": 2, "q": 2}
    neighbors_of = {"m": {"a"}, "p": {"b"}, "q": {"a"}}
    orders = _orders_by_barycenter(layer_by_id, neighbors_of)
    assert orders["q"] == 0
    assert orders["p"] == 1


def test_node_to_dict_carries_layer():
    node = file_node("a.py")
    assert node.to_dict()["layer"] is None
    node.layer = 2
    assert node.to_dict()["layer"] == 2


def test_files_sharing_a_directory_sit_contiguously_after_grouping():
    # Barycenter interleaves these (positions 0,1,2,3 = src/a, tests/test_a,
    # src/b, tests/test_b); grouping should pull the two src files and the
    # two tests files each into a contiguous run.
    order_by_id = {"src/a.py": 0, "tests/test_a.py": 1, "src/b.py": 2, "tests/test_b.py": 3}
    layer_by_id = {node: 0 for node in order_by_id}
    group_by_id = {
        "src/a.py": "src",
        "tests/test_a.py": "tests",
        "src/b.py": "src",
        "tests/test_b.py": "tests",
    }
    grouped = _grouped_by_directory(order_by_id, layer_by_id, group_by_id)
    src_positions = {grouped["src/a.py"], grouped["src/b.py"]}
    test_positions = {grouped["tests/test_a.py"], grouped["tests/test_b.py"]}
    assert max(src_positions) < min(test_positions) or max(test_positions) < min(src_positions)
    # members keep their barycenter order within the group
    assert grouped["src/a.py"] < grouped["src/b.py"]
    assert grouped["tests/test_a.py"] < grouped["tests/test_b.py"]


def test_group_order_follows_mean_barycenter_position_of_members():
    # src's members average to barycenter position 0 (both land at 0 in
    # their own layer since nothing separates them); tests' single member
    # sits at barycenter position 1. Group order should follow: src first.
    order_by_id = {"src/a.py": 0, "src/b.py": 0, "tests/test_a.py": 1}
    layer_by_id = {"src/a.py": 0, "src/b.py": 0, "tests/test_a.py": 0}
    group_by_id = {"src/a.py": "src", "src/b.py": "src", "tests/test_a.py": "tests"}
    grouped = _grouped_by_directory(order_by_id, layer_by_id, group_by_id)
    assert grouped["src/a.py"] < grouped["tests/test_a.py"]
    assert grouped["src/b.py"] < grouped["tests/test_a.py"]


def test_function_bands_are_unaffected_by_directory_grouping():
    flat = [
        file_node("flow.py"),
        function_node("flow.py", "top"),
        function_node("flow.py", "leaf"),
    ]
    nested = [
        file_node("src/pkg/flow.py"),
        function_node("src/pkg/flow.py", "top"),
        function_node("src/pkg/flow.py", "leaf"),
    ]
    edges_for = lambda rel: [calls(f"{rel}::top", f"{rel}::leaf")]
    assign_layers(flat, edges_for("flow.py"))
    assign_layers(nested, edges_for("src/pkg/flow.py"))
    assert orders_of(flat)["flow.py::top"] == orders_of(nested)["src/pkg/flow.py::top"]
    assert orders_of(flat)["flow.py::leaf"] == orders_of(nested)["src/pkg/flow.py::leaf"]


def test_group_for_path_is_top_level_directory_or_root_sentinel():
    assert group_for_path("tests/test_store.py") == "tests"
    assert group_for_path("readme_helper.py") == "."


def test_group_for_path_skips_wrapper_directory_and_uses_package_name():
    assert group_for_path("src/agendabot/bsp/models.py") == "agendabot"
    assert group_for_path("src/agendabot/webhook.py") == "agendabot"
    assert group_for_path("lib/pkg/mod.py") == "pkg"


def test_group_for_path_leaves_non_wrapper_top_level_directories_alone():
    assert group_for_path("tests/bsp/test_twilio.py") == "tests"
    assert group_for_path("scripts/chat.py") == "scripts"


def test_group_for_path_only_a_directory_segment_triggers_the_skip():
    assert group_for_path("src.py") == "."


def test_group_for_path_falls_back_to_wrapper_name_with_no_next_segment():
    assert group_for_path("src/only.py") == "src"


def groups_of(nodes: list[GraphNode]) -> dict[str, str | None]:
    return {node.id: node.group for node in nodes}


def test_assign_layers_sets_group_on_file_nodes_and_none_on_symbols():
    nodes = [
        file_node("src/a.py"),
        file_node("b.py"),
        function_node("src/a.py", "helper"),
    ]
    assign_layers(nodes, [])
    groups = groups_of(nodes)
    assert groups["src/a.py"] == "src"
    assert groups["b.py"] == "."
    assert groups["src/a.py::helper"] is None


def test_grouping_is_deterministic_across_runs():
    def build():
        return [
            file_node("src/a.py"),
            file_node("tests/test_b.py"),
            file_node("src/b.py"),
            file_node("tests/test_a.py"),
        ]

    edges = [
        imports("tests/test_a.py", "src/a.py"),
        imports("tests/test_b.py", "src/b.py"),
    ]
    first = build()
    assign_layers(first, edges)
    second = build()
    assign_layers(second, edges)
    assert orders_of(first) == orders_of(second)
