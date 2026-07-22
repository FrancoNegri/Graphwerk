# 182. `GraphService` wires `uses` edges and propagates status like `calls`

Status: done
Decision: docs/decisions/062-variable-symbols-and-changed-method-blast-radius.md

## Goal

A method/function that references a variable symbol (per ticket 181's
`uses` field) gets a `uses`-kind edge to that variable's node, resolved
through the same shared-tree/import-reachability rules `calls` edges
already use, and that edge participates in blast-radius (`AFFECTED`)
marking and edge-status propagation the same way a `calls` edge does.

## Acceptance criteria

- `GraphService._add_call_edges` (or its renamed/generalized form) is
  parametrized so it runs once for `(SymbolInfo.calls, "calls")` and once
  for `(SymbolInfo.uses, "uses")`, reusing the same target-resolution
  logic (shared-tree check, import-reachability, `allowed_target_statuses`
  by caller-deleted state) rather than a second parallel implementation.
- A method that references an unchanged module-level global produces a
  `GraphEdge(kind="uses")` from the method's node id to the global's node
  id when the method itself is `added`/`modified`/`deleted` (mirroring
  `calls`' existing target-status filtering).
- `_mark_affected` marks an otherwise-`unchanged` variable node
  `AFFECTED` when a `uses` edge from `changed` code targets it — same
  rule already applied for `calls` targeting changed code, generalized to
  `edge.kind in {"calls", "uses"}`.
- `_mark_edge_status` applies its existing status-propagation rules (edge
  takes target's status if target is changed; edge takes source's status
  if source is deleted/added) to `uses` edges the same way it already does
  for `calls` edges.
- A class-level variable used by a method on its *own* class resolves
  (same-file case always works); a module-level global used from a
  different file that imports it resolves through the same import-chain
  logic `calls` already uses — no new resolution code, same function.
- Existing `calls`-edge tests continue to pass unmodified; new tests cover
  `uses` edges end to end (method → variable edge exists, affected marking,
  edge status).

## Likely files

- `graphwerk/service.py` — generalize `_add_call_edges`, `_mark_affected`,
  `_mark_edge_status`.
- `tests/test_service.py` (or wherever `GraphService` snapshot tests
  live) — new `uses`-edge test cases.

## Out of scope

- Frontend rendering of `uses` edges/`variable` nodes — ticket 183.
- Sidebar "Affects" summary — ticket 184.
