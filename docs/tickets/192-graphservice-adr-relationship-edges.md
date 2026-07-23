# 192. `GraphService` wires `supersedes`/`amends`/`extends` edges between ADRs

Status: done
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

An ADR's typed relationship to another ADR (ticket 191's parsed data)
becomes a real, renderable `GraphEdge` in the snapshot.

## Acceptance criteria

- `GraphService.snapshot()` emits one `GraphEdge(source=<this ADR's rel
  path>, target=<named ADR's rel path>, kind=<"supersedes"|"amends"|
  "extends">)` per entry in that ADR file's `FileIndex.adr_relationships`.
- Edges only connect nodes that exist in the current snapshot (an ADR
  referencing a since-deleted file produces no dangling edge) — same
  defensive posture existing edge-wiring (e.g. `_add_import_edges`)
  already takes.
- These are ordinary, undiffed edges (no `status` beyond the default/
  unchanged — ADR relationships aren't something that gets "modified" by
  a code session's diff) — confirm this matches how `references` edges
  are already handled today (no status computation needed).
- A test against fixture ADR files (one superseding, one amending, one
  extending another) asserts all three edge kinds appear with the right
  source/target/kind.

## Likely files

- `graphwerk/service.py` — new edge-wiring step in `snapshot()`.
- `tests/` — snapshot-level test with fixture ADR files.

## Out of scope

- The `grounds` edge from `docs/02-product-concept.md` — ticket 194
  (depends on these edges existing, to know which ADRs have no incoming
  one).
- Frontend rendering — ticket 197.
