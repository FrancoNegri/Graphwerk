# 142. Discard clears all approvals; reject unapproves its path

Status: done
Decision: docs/decisions/050-apply-becomes-approval-scoped-commit.md

## Goal

Keep `ApprovalStore` consistent with the other two reviewer actions that
already exist: discarding the whole change set should not leave stale
approval entries behind, and rejecting a node should pull it back out of
whatever's about to be committed.

## Acceptance criteria

- `POST /api/discard` calls `approval_store.clear_all()` after
  `discard_engine.discard_all()` succeeds (still refused with 409 while a
  session is running, unchanged).
- `POST /api/reject` calls `approval_store.unapprove(rel_path)` for the
  rejected node's file (derive `rel_path` from `req.id` the same way
  `ApplyEngine.reject` already does — `node_id.split("::")[0]`), before
  returning the re-prompt payload.

## Likely files

- `graphwerk/server.py` — both endpoint handlers.
- `tests/test_server.py` — discard-clears-approval, reject-unapproves
  coverage.

## Out of scope

- `ApprovalStore` itself — ticket 139.
- Frontend changes — ticket 144.
