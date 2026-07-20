# 150. Deleted-caller `calls` edges report `DELETED` status

Status: done
Decision: docs/decisions/054-deleted-caller-edge-status.md

## Goal

A `calls` edge whose source symbol was deleted reports edge status
`DELETED` even when its target is `UNCHANGED`, instead of defaulting to
`UNCHANGED` and looking like nothing changed.

## Acceptance criteria

- `_mark_edge_status`: a `calls` edge whose source node has status
  `DELETED` gets `edge.status = Status.DELETED` when the target's own
  status isn't already `MODIFIED`/`ADDED`/`DELETED`.
- Target status still takes priority when the target itself is changed —
  existing behavior, unchanged.
- `imports` edges unaffected.
- New test: a `calls` edge from a deleted source to an unchanged target has
  `DELETED` edge status.
- Existing test
  `test_calls_edge_to_unrelated_target_from_affected_source_has_unchanged_status`
  still passes unmodified.

## Likely files

- `graphwerk/service.py` — `_mark_edge_status`.
- `tests/test_service.py` — new test case.

## Out of scope

- Collapsed-representative-edge status aggregation (`static/app.js`
  `toElements` keeps the first raw call's status, not the most severe) —
  separate ticket/decision later.
- `imports` edges — still always `UNCHANGED` per ADR 016.
