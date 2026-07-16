# 036. `GraphNode.group` in the snapshot payload

Status: done
Decision: docs/decisions/010-directory-band-grouping.md

## Goal

File nodes carry their grouping key (top-level directory) in the
`/api/graph` payload, so the UI can show the grouping the ordering uses
without deriving it client-side.

## Acceptance criteria

- `GraphNode` gains a `group` field: top-level directory for file nodes
  (`"src"`, `"tests"`, a sentinel like `"."` for repo-root files), `null`
  for symbol nodes. The same derivation the ordering pass uses — one
  helper, two call sites, no duplicated path-splitting.
- `/api/graph` includes the field; existing fields unchanged (pytest on
  the serialized snapshot).
- Demo instance: all `shop/*` file nodes report group `"shop"`.

## Likely files

- `graphwerk/models.py` — field
- `graphwerk/service.py` or `graphwerk/layout.py` — shared derivation helper
- `tests/` — payload coverage

## Out of scope

- UI consumption (ticket 037).
