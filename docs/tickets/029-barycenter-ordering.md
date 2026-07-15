# 029. Within-layer ordering utility (barycenter sweeps)

Status: done
Decision: docs/decisions/008-within-layer-ordering.md

## Goal

`graphwerk/layout.py` gains a pure function that, given a layer assignment
and adjacency for one graph, returns a deterministic left-to-right order
index per node that places cross-layer neighbors near each other.

## Acceptance criteria

- A function (e.g. `_orders_by_barycenter(layer_by_id, neighbors_of)`)
  returns `dict[str, int]`: for each node, its 0-based position within its
  layer.
- Initial order is deterministic (sorted by node id); a fixed number of
  alternating downward/upward sweeps re-sorts each layer by the mean
  position of neighbors in the adjacent layer, treating edges as
  undirected for adjacency (an edge in either direction between adjacent
  layers counts).
- Nodes with no neighbors in the adjacent layer, and barycenter ties, keep
  their previous relative order (stable sort) — same input always yields
  the same output.
- Edges spanning more than one layer contribute via the neighbor's actual
  position in its own layer (no dummy nodes).
- Test cases include: a two-layer graph where the naive id-order crosses
  edges and the result uncrosses them; a node with no cross-layer
  neighbors keeping its slot; determinism (two runs, equal output); a
  single-layer graph (orders are just the stable initial order).

## Likely files

- `graphwerk/layout.py` — new ordering function alongside
  `_layers_by_longest_path`
- `tests/test_layout.py` — algorithm-level tests

## Out of scope

Wiring into `assign_layers`/snapshot or the `GraphNode.order` field
(ticket 030); any `app.js` change (ticket 031).
