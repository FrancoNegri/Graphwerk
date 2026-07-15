"""Layer assignment for graph nodes: longest-path depth over the graph's
edges, with cycles collapsed into one shared layer via strongly connected
components.

Files get an import-depth layer (a file importing nothing sits in layer 0);
top-level functions get a call-depth layer scoped to their own file's
functions. The UI reads ``GraphNode.layer`` and only maps it to layout
constraints — it never re-derives graph structure (ADR 005).
"""

from __future__ import annotations

from graphwerk.models import GraphEdge, GraphNode


def assign_layers(nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
    layer_by_id = _file_layers_by_import_depth(nodes, edges)
    layer_by_id.update(_function_layers_by_call_depth(nodes, edges))
    for node in nodes:
        node.layer = layer_by_id.get(node.id)


def _file_layers_by_import_depth(
    nodes: list[GraphNode], edges: list[GraphEdge]
) -> dict[str, int]:
    imported_files_of: dict[str, set[str]] = {
        node.id: set() for node in nodes if node.kind == "file"
    }
    for edge in edges:
        if edge.kind != "imports":
            continue
        if edge.source != edge.target and edge.source in imported_files_of and edge.target in imported_files_of:
            imported_files_of[edge.source].add(edge.target)
    return _layers_by_longest_path(imported_files_of)


def _function_layers_by_call_depth(
    nodes: list[GraphNode], edges: list[GraphEdge]
) -> dict[str, int]:
    file_ids = {node.id for node in nodes if node.kind == "file"}
    functions_by_file: dict[str, set[str]] = {}
    for node in nodes:
        if node.kind == "function" and node.parent in file_ids:
            functions_by_file.setdefault(node.parent, set()).add(node.id)

    layers: dict[str, int] = {}
    for function_ids in functions_by_file.values():
        callees_of: dict[str, set[str]] = {fid: set() for fid in function_ids}
        for edge in edges:
            if edge.kind != "calls":
                continue
            if edge.source in callees_of and edge.target in function_ids:
                callees_of[edge.source].add(edge.target)
        layers.update(_layers_by_longest_path(callees_of))
    return layers


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

    # Tarjan emits components in reverse topological order, so everything a
    # component points at already has its layer by the time we reach it.
    component_layer = [0] * component_count
    for component in range(component_count):
        for neighbor in neighbor_components[component]:
            component_layer[component] = max(component_layer[component], component_layer[neighbor] + 1)

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
