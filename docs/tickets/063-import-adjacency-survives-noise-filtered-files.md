# 063. Import adjacency survives noise-filtered intermediate files

Status: ready
Decision: docs/decisions/023-import-adjacency-drops-noise-filtered-and-test-edges.md

## Goal

A file with no extracted symbols (e.g. all-imports-plus-a-dict, like
agendabot's `handlers.py`) still gets skipped as a displayed `GraphNode`
(existing noise filter, unchanged), but its `imports` edges still count
toward layering everything on either side of it — so a file reachable only
*through* a noise-filtered file gets its real (deeper) layer instead of
falsely looking like a root.

## Acceptance criteria

- `_import_adjacency` in `graphwerk/layout.py` builds `imported_files_of`
  from the union of displayed file nodes and every `imports` edge's
  endpoints (`setdefault` both sides before recording the edge), instead of
  requiring both endpoints to already be keys from `nodes`.
- New test mirroring the dogfood shape: three files `a.py -> b.py ->
  c.py` where `b.py`'s node is absent from the `nodes` list passed to
  `assign_layers` (simulating the noise filter) but an `a.py -> b.py` and
  `b.py -> c.py` `imports` edge both exist in `edges`. Assert `a.py == 0`
  and `c.py == 2` (not `0`) — `c.py` keeps its true depth despite `b.py`
  never appearing as a node.
- Existing isolated-file case (a file with zero import edges) still gets
  layer 0 — confirm the seed-from-nodes behavior for that case is
  unaffected.
- All existing `_import_adjacency`/`_layers_by_longest_path` tests in
  `tests/test_layout.py` still pass unmodified (this only widens which
  edges are counted; it doesn't change the propagation direction from
  ticket 061).

## Likely files

- `graphwerk/layout.py` — `_import_adjacency`.
- `tests/test_layout.py` — new noise-filtered-intermediate-file case.

## Out of scope

- Excluding test-file edges (ticket 064 — separate concern: this ticket is
  purely "don't silently drop real edges," that one is "some edges
  shouldn't count at all").
- Any change to `_call_adjacencies_by_file` (ADR 023 — the noise filter
  never drops function nodes, so this problem doesn't reach them).
