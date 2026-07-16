# 061. Layer by longest path from entry points, not to leaves

Status: done
Decision: docs/decisions/022-entry-points-anchor-top-layer.md

## Goal

`_layers_by_longest_path` computes each node's layer as the longest chain
of edges reachable from a **root** (a file nothing imports, or a function
nothing calls) descending toward what it depends on, instead of the
longest chain to a sink — so every entry point lands at layer 0 together,
regardless of how deep its own dependency tree happens to go.

## Acceptance criteria

- A root (no incoming edges within the adjacency being layered) is always
  layer 0.
- For every edge `source -> target` in the adjacency, the result satisfies
  `layer(target) >= layer(source) + 1` — a node's layer is always strictly
  greater than anything that points at it.
- `test_files_layered_by_import_depth` (a.py imports b.py imports c.py)
  updates to: `a.py == 0`, `b.py == 1`, `c.py == 2` (root importer at 0,
  descending).
- `test_diamond_import_takes_longest_path` (a imports b,d; b imports c; c
  imports d) updates to assert `d.py == 3` (the deepest sink) and
  `a.py == 0` (the root), mirroring the current a.py==3 assertion.
- `test_import_cycle_collapses_into_one_shared_layer` (x<->y cycle, y
  imports base) updates to: `x.py == y.py == 0` (the cycle has no incoming
  edge from outside, so it's a root), `base.py == 1`.
- `test_functions_layered_by_intra_file_call_depth` (top calls middle
  calls leaf) updates to: `top == 0`, `middle == 1`, `leaf == 2`.
- `test_mutual_recursion_shares_a_layer_and_caller_sits_above` (driver
  calls ping/pong cycle) updates to: `driver == 0`, `ping == pong == 1`.
- `test_snapshot_assigns_layers_to_files_and_functions` in
  `tests/test_service.py` updates to: `main.py == 0`, `pipeline.py == 1`,
  `report == 0`, `parse == 1`, `load == 2`.
- A new test with two unrelated entry points at different dependency-tree
  depths (mirroring the dogfood observation — one entry importing a
  shallow chain, another importing a deep one) confirms both entry points
  land at layer 0 despite the differing depths beneath them.
- Tests unaffected by direction (no edges at all, self-recursion, cross-
  file calls excluded from the adjacency, classes/methods getting no
  layer) are left as-is — confirm they still pass instead of guessing.
- Module docstring and the `_layers_by_longest_path`/loop comments in
  `graphwerk/layout.py` are corrected to describe the new direction (a
  root is "nothing imports/calls it," not "it imports/calls nothing").

## Likely files

- `graphwerk/layout.py` — `_layers_by_longest_path`: reverse the
  iteration order over components and swap which side of the update gets
  `max`'d; update the docstring/comments describing the algorithm.
- `tests/test_layout.py` — mirrored expected values plus the new
  multiple-entry-points case.
- `tests/test_service.py` — mirrored expected values in
  `test_snapshot_assigns_layers_to_files_and_functions`.

## Out of scope

- `static/app.js`'s rendering comparator (ticket 062, depends on this
  ticket) — that's a separate concern (which end renders "up"), not the
  layer computation itself.
- `_orders_by_barycenter` and `_grouped_by_directory` — both operate
  purely on numeric layer values and need no change (ADR 022).
