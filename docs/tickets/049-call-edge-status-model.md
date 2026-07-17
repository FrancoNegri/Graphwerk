# 049. `GraphEdge.status` computed for `calls` edges

Status: done
Decision: docs/decisions/016-call-edge-status.md

## Goal

Every `calls` edge carries a `status` reflecting whether it leads into
changed code, so the UI can color it without duplicating graph-algorithm
logic client-side.

## Acceptance criteria

- `GraphEdge` gains `status: Status = Status.UNCHANGED`, included in
  `to_dict()`.
- For `calls` edges: `status` = target node's status when that status is
  `MODIFIED`, `ADDED`, or `DELETED`; else `UNCHANGED`. (Corrected
  2026-07-17, audit F-003: the originally specified `AFFECTED` branch —
  affected source into unchanged target — shipped, then was removed as an
  over-tagging bug in commit cfb4832; see the ADR 016 amendment. No edge
  is ever `affected`.)
- `imports` edges always keep `status = UNCHANGED`.
- Computed in `GraphService` alongside/after `_mark_affected` (needs final
  node statuses, including `AFFECTED`), not in `static/app.js`.
- Unit tests in the service layer cover: edge into a modified target, edge
  into an added target, edge into a deleted target, an edge out of an
  `AFFECTED` source into an unchanged target (stays `UNCHANGED`, per the
  correction above), an unrelated unchanged-to-unchanged edge, and an
  `imports` edge (stays `UNCHANGED` even when endpoints changed).

## Likely files

- `graphwerk/models.py` — `GraphEdge.status` field + `to_dict`.
- `graphwerk/service.py` — new step computing edge status, wired into the
  existing `_add_call_edges` → `_add_import_edges` → `_mark_affected`
  pipeline.
- `tests/test_service.py` — new cases for the edge-status rule.

## Out of scope

- Any client-side change (tickets 050-051).
- `imports` edge status beyond always-`UNCHANGED`.
