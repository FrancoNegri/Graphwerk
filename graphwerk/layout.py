"""Layer assignment for graph nodes: longest-path depth from each root over
the graph's edges, with cycles collapsed into one shared layer via strongly
connected components.

Files get an import-depth layer (a file nothing imports sits in layer 0,
same as every other root, regardless of how deep its own dependency tree
descends — ADR 022); top-level functions get a call-depth layer scoped to
their own file's functions, anchored the same way on functions nothing
calls. ADRs get a bottom-up lineage layer from the same longest-path helper,
walked over `supersedes`/`amends`/`extends` edges and shifted by one so a
founding ADR (nothing narrows it) lands at layer 1; `docs/02-product-
concept.md` is pinned at layer 0 and ticket nodes get no layer at all
(ADR 066). Within each layer, barycenter sweeps assign a left-to-right
order that pulls cross-layer neighbors close (ADR 008). For the file band
only, that order is then re-sorted so files sharing a top-level directory
sit contiguously, group order following the mean barycenter position of its
members (ADR 010). The UI reads ``GraphNode.layer``/``GraphNode.order`` and
only maps them to layout constraints — it never re-derives graph structure
(ADR 005).
"""

from __future__ import annotations

import re

from graphwerk.models import GraphEdge, GraphNode


_WRAPPER_DIRECTORY_NAMES = {"src", "lib"}

# docs/02-product-concept.md's node (ADR 065's grounds-edge source, ADR
# 066's layer-0 anchor for the doc domain).
PRODUCT_CONCEPT_PATH = "docs/02-product-concept.md"

_ADR_PATH = re.compile(r"^docs/decisions/\d+-")
_TICKET_PATH = re.compile(r"^docs/tickets/\d+-")
_ADR_RELATIONSHIP_KINDS = {"supersedes", "amends", "extends"}


def group_for_path(path: str) -> str:
    """Top-level directory of a file path; "." for repo-root files. A
    generic wrapper directory (src/lib) is skipped in favor of the next
    segment, so src-layout packages group by package name instead of
    collapsing into one indistinguishable "src" (ADR 021)."""
    directory = path.rpartition("/")[0]
    if not directory:
        return "."
    segments = directory.split("/")
    if segments[0] in _WRAPPER_DIRECTORY_NAMES and len(segments) > 1:
        return segments[1]
    return segments[0]


def assign_layers(nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
    group_by_id = {node.id: group_for_path(node.path) for node in nodes if node.kind == "file"}
    path_by_id = {node.id: node.path for node in nodes if node.kind == "file"}
    paired_file_by_test_id = pair_tests_with_files(nodes)
    layer_by_id: dict[str, int] = {}
    order_by_id: dict[str, int] = {}
    for is_file_graph, neighbors_of in _layered_adjacencies(nodes, edges, set(paired_file_by_test_id)):
        layers = _layers_by_longest_path(neighbors_of)
        if is_file_graph:
            layers = _sink_dangling_tests_to_bottom_layer(layers, path_by_id)
        layer_by_id.update(layers)
        orders = _orders_by_barycenter(layers, neighbors_of)
        if is_file_graph:
            orders = _grouped_by_directory(orders, layers, group_by_id)
        order_by_id.update(orders)
    _apply_doc_domain_layers(nodes, edges, layer_by_id)
    for node in nodes:
        node.layer = layer_by_id.get(node.id)
        node.order = order_by_id.get(node.id)
        node.group = group_by_id.get(node.id)
        node.paired_file = paired_file_by_test_id.get(node.id)


def _apply_doc_domain_layers(
    nodes: list[GraphNode], edges: list[GraphEdge], layer_by_id: dict[str, int]
) -> None:
    """Overrides the file-import pass's result for the doc domain (ADR
    066): ADRs get a bottom-up lineage layer computed independently over
    `supersedes`/`amends`/`extends` edges, `docs/02-product-concept.md` is
    pinned at layer 0, and ticket nodes get no layer at all."""
    for adr_id, base_layer in _layers_by_longest_path(_adr_relationship_adjacency(nodes, edges)).items():
        layer_by_id[adr_id] = base_layer + 1
    for node in nodes:
        if node.kind != "file":
            continue
        if node.id == PRODUCT_CONCEPT_PATH:
            layer_by_id[node.id] = 0
        elif _TICKET_PATH.match(node.id):
            layer_by_id.pop(node.id, None)


def _adr_relationship_adjacency(nodes: list[GraphNode], edges: list[GraphEdge]) -> dict[str, set[str]]:
    """Narrower ADR -> ADR it narrows, the same `source -> target` direction
    the edges themselves already carry (ADR 065). An ADR with no incoming
    edge here is a "founding" ADR — the same no-incoming-edge definition
    `_add_grounds_edges` already uses for the `grounds` edge target, just
    recomputed independently (no shared code, no edge-ordering dependency)."""
    adr_ids = {node.id for node in nodes if node.kind == "file" and _ADR_PATH.match(node.id)}
    neighbors_of: dict[str, set[str]] = {adr_id: set() for adr_id in adr_ids}
    for edge in edges:
        if edge.kind in _ADR_RELATIONSHIP_KINDS and edge.source in adr_ids and edge.target in adr_ids:
            neighbors_of[edge.source].add(edge.target)
    return neighbors_of


def _layered_adjacencies(
    nodes: list[GraphNode], edges: list[GraphEdge], excluded_from_file_graph: set[str]
) -> list[tuple[bool, dict[str, set[str]]]]:
    """One independently layered/ordered graph each: files by imports, then
    every file's top-level functions by intra-file calls (ADR 003). Each
    entry is tagged with whether it's the file graph, the only one directory
    grouping (ADR 010) applies to."""
    return [
        (True, _import_adjacency(nodes, edges, excluded_from_file_graph)),
        *((False, adjacency) for adjacency in _call_adjacencies_by_file(nodes, edges)),
    ]


_TEST_PATH_SEGMENTS = {"tests", "test"}


def is_test_path(path: str) -> bool:
    """A file counts as a test file by pytest's own discovery convention:
    a tests/test-named path segment, or a test_*.py/*_test.py filename."""
    filename = path.rpartition("/")[2]
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True
    segments = path.split("/")[:-1]
    return any(segment in _TEST_PATH_SEGMENTS for segment in segments)


def _drop_wrapper_rooted_prefix(path: str) -> str:
    """Path with its top-level directory dropped; a generic wrapper
    directory (src/lib) also drops the package-root segment after it, the
    same convention `group_for_path` already applies (ADR 021) — a
    src-layout source file's mirror key needs to line up with a flat
    tests/ tree that never had the package-root segment to begin with
    (ADR 041 amendment)."""
    if "/" not in path:
        return path
    top, remainder = path.split("/", 1)
    if top in _WRAPPER_DIRECTORY_NAMES and "/" in remainder:
        remainder = remainder.split("/", 1)[1]
    return remainder


def _mirror_key(path: str) -> str:
    """Test files additionally drop a leading tests/test segment and a
    test_/_test filename affix, so a test file's key lines up with the
    source file it mirrors (ADR 041)."""
    remainder = _drop_wrapper_rooted_prefix(path)
    if not is_test_path(path):
        return remainder
    segments = remainder.split("/")
    if segments[0] in _TEST_PATH_SEGMENTS and len(segments) > 1:
        segments = segments[1:]
    *directory_segments, filename = segments
    if filename.startswith("test_"):
        filename = filename.removeprefix("test_")
    elif filename.endswith("_test.py"):
        filename = filename.removesuffix("_test.py") + ".py"
    return "/".join([*directory_segments, filename])


def pair_tests_with_files(nodes: list[GraphNode]) -> dict[str, str]:
    """Maps each test file node id to the one source file node id sharing
    its mirror key. No match, or more than one candidate, is left unpaired —
    no arbitrary tie-break (ADR 041)."""
    file_nodes = [node for node in nodes if node.kind == "file"]
    source_ids_by_key: dict[str, list[str]] = {}
    for node in file_nodes:
        if not is_test_path(node.path):
            source_ids_by_key.setdefault(_mirror_key(node.path), []).append(node.id)

    paired: dict[str, str] = {}
    for node in file_nodes:
        if not is_test_path(node.path):
            continue
        candidates = source_ids_by_key.get(_mirror_key(node.path), [])
        if len(candidates) == 1:
            paired[node.id] = candidates[0]
    return paired


def _import_adjacency(
    nodes: list[GraphNode], edges: list[GraphEdge], excluded: set[str]
) -> dict[str, set[str]]:
    imported_files_of: dict[str, set[str]] = {
        node.id: set() for node in nodes if node.kind == "file" and node.id not in excluded
    }
    for edge in edges:
        if edge.kind != "imports" or edge.source == edge.target:
            continue
        if is_test_path(edge.source):
            continue
        if edge.source in excluded or edge.target in excluded:
            continue
        imported_files_of.setdefault(edge.source, set())
        imported_files_of.setdefault(edge.target, set())
        imported_files_of[edge.source].add(edge.target)
    return imported_files_of


def _sink_dangling_tests_to_bottom_layer(
    layers: dict[str, int], path_by_id: dict[str, str]
) -> dict[str, int]:
    """A dangling test file (still present here, since paired ones are
    excluded from the file graph entirely) has no import adjacency of its
    own and would otherwise settle at layer 0 next to real entry points.
    Push it one layer past the deepest ordinary file instead, so it reads
    as peripheral rather than architecturally central (ADR 043)."""
    ordinary_layers = [layer for node_id, layer in layers.items() if not is_test_path(path_by_id.get(node_id, ""))]
    bottom_layer = max(ordinary_layers) + 1 if ordinary_layers else 0
    return {
        node_id: bottom_layer if is_test_path(path_by_id.get(node_id, "")) else layer
        for node_id, layer in layers.items()
    }


def _call_adjacencies_by_file(
    nodes: list[GraphNode], edges: list[GraphEdge]
) -> list[dict[str, set[str]]]:
    file_ids = {node.id for node in nodes if node.kind == "file"}
    functions_by_file: dict[str, set[str]] = {}
    for node in nodes:
        if node.kind == "function" and node.parent in file_ids:
            functions_by_file.setdefault(node.parent, set()).add(node.id)

    adjacencies: list[dict[str, set[str]]] = []
    for function_ids in functions_by_file.values():
        callees_of: dict[str, set[str]] = {fid: set() for fid in function_ids}
        for edge in edges:
            if edge.kind != "calls":
                continue
            if edge.source in callees_of and edge.target in function_ids:
                callees_of[edge.source].add(edge.target)
        adjacencies.append(callees_of)
    return adjacencies


_BARYCENTER_SWEEPS = 4


def _orders_by_barycenter(
    layer_by_id: dict[str, int], neighbors_of: dict[str, set[str]]
) -> dict[str, int]:
    linked_to = _undirected_adjacency(layer_by_id, neighbors_of)

    nodes_by_layer: dict[int, list[str]] = {}
    for node in sorted(layer_by_id):
        nodes_by_layer.setdefault(layer_by_id[node], []).append(node)

    position: dict[str, int] = {}
    for layer_nodes in nodes_by_layer.values():
        position.update({node: index for index, node in enumerate(layer_nodes)})

    for sweep in range(_BARYCENTER_SWEEPS):
        toward_higher_layers = sweep % 2 == 0
        for layer in sorted(nodes_by_layer, reverse=not toward_higher_layers):
            layer_nodes = nodes_by_layer[layer]
            barycenter = {
                node: _neighbor_position_mean(
                    node, layer, layer_by_id, linked_to, position, toward_higher_layers
                )
                for node in layer_nodes
            }
            layer_nodes.sort(key=barycenter.__getitem__)
            position.update({node: index for index, node in enumerate(layer_nodes)})
    return position


def _grouped_by_directory(
    order_by_id: dict[str, int],
    layer_by_id: dict[str, int],
    group_by_id: dict[str, str],
) -> dict[str, int]:
    """Re-sorts each layer so files sharing a top-level directory sit
    contiguously; group order follows the mean barycenter position of its
    members, members keeping their barycenter order within the group (ADR 010)."""
    nodes_by_layer: dict[int, list[str]] = {}
    for node_id in sorted(order_by_id, key=order_by_id.get):
        nodes_by_layer.setdefault(layer_by_id[node_id], []).append(node_id)

    grouped_order: dict[str, int] = {}
    for layer_nodes in nodes_by_layer.values():
        members_by_group: dict[str, list[str]] = {}
        for node_id in layer_nodes:
            members_by_group.setdefault(group_by_id.get(node_id, node_id), []).append(node_id)
        ordered_groups = sorted(
            members_by_group.values(),
            key=lambda members: sum(order_by_id[m] for m in members) / len(members),
        )
        position = 0
        for members in ordered_groups:
            for node_id in members:
                grouped_order[node_id] = position
                position += 1
    return grouped_order


def _undirected_adjacency(
    layer_by_id: dict[str, int], neighbors_of: dict[str, set[str]]
) -> dict[str, set[str]]:
    linked_to: dict[str, set[str]] = {node: set() for node in layer_by_id}
    for node, neighbors in neighbors_of.items():
        for neighbor in neighbors:
            if node != neighbor and node in linked_to and neighbor in linked_to:
                linked_to[node].add(neighbor)
                linked_to[neighbor].add(node)
    return linked_to


def _neighbor_position_mean(
    node: str,
    layer: int,
    layer_by_id: dict[str, int],
    linked_to: dict[str, set[str]],
    position: dict[str, int],
    toward_higher_layers: bool,
) -> float:
    # Sweeping toward higher layers means each layer looks at the (already
    # re-sorted) layers below it, and vice versa. A neighbor further than one
    # layer away still counts, via its position in its own layer (no dummy
    # nodes). Nodes with nothing to look at keep their current slot as key,
    # so the stable sort preserves their order.
    if toward_higher_layers:
        relevant = [position[n] for n in linked_to[node] if layer_by_id[n] < layer]
    else:
        relevant = [position[n] for n in linked_to[node] if layer_by_id[n] > layer]
    if not relevant:
        return float(position[node])
    return sum(relevant) / len(relevant)


def _layers_by_longest_path(neighbors_of: dict[str, set[str]]) -> dict[str, int]:
    component_of, component_count = _strongly_connected_components(neighbors_of)

    neighbor_components: list[set[int]] = [set() for _ in range(component_count)]
    for node, neighbors in neighbors_of.items():
        for neighbor in neighbors:
            source, target = component_of[node], component_of[neighbor]
            if source != target:
                neighbor_components[source].add(target)

    # Tarjan emits components in reverse topological order, so a root (no
    # incoming edges from outside the component) is emitted last. Walking
    # that order backward means, by the time we reach a component, every
    # component that points at it has already pushed its layer forward.
    component_layer = [0] * component_count
    for component in reversed(range(component_count)):
        for neighbor in neighbor_components[component]:
            component_layer[neighbor] = max(component_layer[neighbor], component_layer[component] + 1)

    return {node: component_layer[component_of[node]] for node in neighbors_of}


def _strongly_connected_components(
    neighbors_of: dict[str, set[str]],
) -> tuple[dict[str, int], int]:
    """Iterative Tarjan — explicit stack so deep graphs can't hit the
    recursion limit. Self-loops are tolerated (a node alone in its cycle
    is its own component)."""
    visit_index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    component_of: dict[str, int] = {}
    component_count = 0
    next_index = 0

    for start in neighbors_of:
        if start in visit_index:
            continue
        pending: list[list] = [[start, 0]]
        while pending:
            node, neighbor_position = pending[-1]
            if neighbor_position == 0:
                visit_index[node] = lowlink[node] = next_index
                next_index += 1
                stack.append(node)
                on_stack.add(node)
            neighbors = list(neighbors_of[node])
            if neighbor_position < len(neighbors):
                pending[-1][1] += 1
                neighbor = neighbors[neighbor_position]
                if neighbor not in visit_index:
                    pending.append([neighbor, 0])
                elif neighbor in on_stack:
                    lowlink[node] = min(lowlink[node], visit_index[neighbor])
            else:
                pending.pop()
                if pending:
                    caller = pending[-1][0]
                    lowlink[caller] = min(lowlink[caller], lowlink[node])
                if lowlink[node] == visit_index[node]:
                    while True:
                        member = stack.pop()
                        on_stack.remove(member)
                        component_of[member] = component_count
                        if member == node:
                            break
                    component_count += 1
    return component_of, component_count
