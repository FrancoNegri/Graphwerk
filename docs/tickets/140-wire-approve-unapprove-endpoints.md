# 140. `/api/apply` marks approval; add `/api/unapprove`

Status: ready
Decision: docs/decisions/050-apply-becomes-approval-scoped-commit.md

## Goal

Stop `/api/apply` from writing to the base tree immediately — it should
mark the path approved instead — and add the endpoint to undo that.

## Acceptance criteria

- `POST /api/apply {"path": ...}` calls `approval_store.approve(path)` and
  returns a response the frontend can use to reflect approved state (no
  file is copied to base as a side effect of this call anymore).
- `POST /api/unapprove {"path": ...}` calls `approval_store.unapprove(path)`.
- `create_app` (`graphwerk/server.py`) takes the `ApprovalStore` as a new
  parameter; `build_app` (`graphwerk/bootstrap.py`) constructs one
  (`ApprovalStore(staged)`) and threads it through.
- `ApplyEngine.apply_file` itself is untouched — still available for
  ticket 141's `CommitEngine` to call directly.

## Likely files

- `graphwerk/server.py` — `/api/apply` behavior change, new
  `/api/unapprove` route, `create_app` signature.
- `graphwerk/bootstrap.py` — construct and thread `ApprovalStore`.
- `tests/test_server.py` — update existing apply-endpoint expectations,
  add unapprove coverage.

## Out of scope

- `CommitEngine` scoping to approved paths — ticket 141.
- Reject/discard interaction with approval — ticket 142.
