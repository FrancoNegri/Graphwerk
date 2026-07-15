# 030. `GraphNode.order` in the snapshot payload

Status: ready
Decision: docs/decisions/008-within-layer-ordering.md

## Goal

Every node that has a `layer` also carries an `order` (its within-layer
position) in the `/api/graph` payload — files ordered by import adjacency,
top-level functions per file by intra-file call adjacency.

## Acceptance criteria

- `GraphNode` gains `order: int | None = None`, serialized by `to_dict()`,
  mirroring `layer`'s contract (integer for files and top-level functions,
  `null` otherwise).
- Layer assignment (`assign_layers`, called from `GraphService.snapshot()`)
  also assigns orders, reusing the ticket 029 utility on the same two
  graphs it already builds: file/import and per-file function/call.
- Functions are ordered within their own file only, independent of other
  files (ADR 003's file-local framing).
- A snapshot-level test asserts that two files in adjacent layers connected
  by an import get nearby orders while an unrelated file does not sit
  between them, and that classes/methods have `order is None`.

## Likely files

- `graphwerk/models.py` — `order` field + serialization
- `graphwerk/layout.py` — call the ordering utility from `assign_layers`
- `tests/test_layout.py`, `tests/test_models.py` — wiring + serialization
  tests

## Out of scope

The ordering algorithm itself (ticket 029); consuming `order` in the UI
(ticket 031).
