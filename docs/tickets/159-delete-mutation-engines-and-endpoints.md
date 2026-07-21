# 159. Delete the file-mutation engines and their endpoints

Status: done
Decision: docs/decisions/058-retire-worktree-single-directory-review.md

## Goal

Graphwerk stops writing to disk anywhere. `ApplyEngine`, `ApprovalStore`,
`CommitEngine`, `DiscardEngine`, and the `/api/apply`, `/api/unapprove`,
`/api/commit`, `/api/discard`, `/api/reject` endpoints are removed.
Landing or undoing a reviewed change becomes the developer's own plain git
operation, outside graphwerk.

## Acceptance criteria

- `/api/apply`, `/api/unapprove`, `/api/commit`, `/api/discard`,
  `/api/reject` no longer exist (404, not just inert).
- `graphwerk/apply.py`, `graphwerk/approval.py`, `graphwerk/commit.py`,
  `graphwerk/discard.py` are deleted; no remaining imports reference them.
- `create_app()` no longer takes `engine`, `commit_engine`,
  `discard_engine`, or `approval_store` parameters.
- `/api/graph` and `/api/session` continue to work unchanged.
- `graphwerk/bootstrap.py` no longer constructs any of the deleted engines.

## Likely files

- `graphwerk/server.py` — remove the five endpoints and their request
  models (`ApplyRequest`, `CommitRequest`, `RejectRequest`), shrink
  `create_app()`'s signature.
- `graphwerk/apply.py`, `graphwerk/approval.py`, `graphwerk/commit.py`,
  `graphwerk/discard.py` — delete.
- `graphwerk/bootstrap.py` — drop construction of the deleted engines.

## Out of scope

- `GraphNode.approved` and the frontend UI that called these endpoints
  (ticket 160) — remove those first or in the same pass if leaving them
  temporarily would make the app render a dead toggle; either order is
  fine as long as both land together.
