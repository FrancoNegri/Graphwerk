# 141. `CommitEngine.commit_all` scoped to approved files

Status: done
Decision: docs/decisions/050-apply-becomes-approval-scoped-commit.md

## Goal

Commit only the files the reviewer approved, not every file that happens
to still differ from base — enabling true partial commit and closing the
gap where an individually-approved-but-uncommitted file could be silently
skipped.

## Acceptance criteria

- `CommitEngine.commit_all` computes `changed_paths` as before, then
  restricts the actual apply/`git add`/`git commit` set to the intersection
  with `approval_store.approved_paths()`.
- Raises `CommitError("nothing approved to commit")` when that intersection
  is empty, distinct from the existing "change set is empty" message.
- On successful commit, calls `approval_store.clear(committed_paths)` so
  those approvals don't linger into the next cycle.
- A file that was approved but reverted back to matching base before commit
  (no longer in `changed_paths`) is silently excluded, not an error.
- `CommitEngine.__init__` takes `ApprovalStore` as a new constructor
  parameter; `bootstrap.py` passes the one built in ticket 140.

## Likely files

- `graphwerk/commit.py` — scoping + clear-on-success logic.
- `graphwerk/bootstrap.py` — pass `ApprovalStore` into `CommitEngine`.
- `tests/test_commit.py` — partial-approval commit, empty-approval error,
  stale-approval exclusion, post-commit clearing.

## Out of scope

- Grouped/multi-select approval UI — file-by-file only.
- Discard/reject wiring — ticket 142.
