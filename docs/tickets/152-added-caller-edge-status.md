# 152. Added-caller `calls` edges report `ADDED` status

Status: done
Decision: docs/decisions/054-deleted-caller-edge-status.md (amended)

## Goal

A `calls` edge whose source symbol was added reports edge status `ADDED`
even when its target is `UNCHANGED`, instead of defaulting to `UNCHANGED`
and looking like nothing changed — the `ADDED` mirror of ticket 150's
`DELETED` fix, same underlying rule (ADR 054, amended).

## Acceptance criteria

- `_mark_edge_status`: a `calls` edge whose source node has status
  `ADDED` gets `edge.status = Status.ADDED` when the target's own status
  isn't already `MODIFIED`/`ADDED`/`DELETED`.
- The existing `DELETED`-source branch from ticket 150 is preserved
  unchanged — both conditions can be expressed as one check against
  `{Status.DELETED, Status.ADDED}`, taking `status_by_id[edge.source]`.
- Target status still takes priority when the target itself is changed —
  existing behavior, unchanged.
- `MODIFIED` sources are NOT given this treatment — out of scope per ADR
  054's amendment (would need hunk-to-symbol mapping the differ doesn't
  do).
- New test: a `calls` edge from an added source to an unchanged target has
  `ADDED` edge status (mirrors the existing deleted-source test from
  ticket 150).
- Existing tests (target-based status, the AFFECTED-source case, and
  ticket 150's deleted-source case) still pass unmodified.

## Likely files

- `graphwerk/service.py` — `_mark_edge_status`.
- `tests/test_service.py` — new test case alongside ticket 150's.

## Out of scope

- `MODIFIED` sources — excluded per ADR 054's amendment.
- Collapsed-representative-edge status aggregation — covered separately by
  ticket 151 / ADR 055.
- `imports` edges — still always `UNCHANGED` per ADR 016.
