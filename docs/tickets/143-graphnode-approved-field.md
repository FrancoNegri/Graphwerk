# 143. `GraphNode.approved` field in the snapshot

Status: ready
Decision: docs/decisions/050-apply-becomes-approval-scoped-commit.md

## Goal

Make approval state reload-safe by serving it from the server-held
`ApprovalStore` on every snapshot, instead of the frontend having to
remember which files it clicked "approve" on (same reload-safety pattern
ADR 042 used for the commit message).

## Acceptance criteria

- `GraphNode` gains `approved: bool = False`, included in `to_dict()`.
- `GraphService.snapshot()` sets it from `approval_store.is_approved(rel)`
  for file nodes; always `False` for symbol nodes.
- `GraphService.__init__` takes `ApprovalStore` as a new parameter;
  `bootstrap.py` passes the shared instance.
- A file approved via `/api/apply`, then re-fetched via `/api/graph`,
  shows `approved: true`; after its content changes (fingerprint mismatch),
  the next `/api/graph` shows `approved: false` again.

## Likely files

- `graphwerk/models.py` — `GraphNode.approved` field + `to_dict`.
- `graphwerk/service.py` — `GraphService` constructor + `snapshot()`.
- `graphwerk/bootstrap.py` — thread `ApprovalStore` into `GraphService`.
- `tests/test_service.py` (or equivalent) — approved-field coverage.

## Out of scope

- Frontend consumption of the field — ticket 144.
