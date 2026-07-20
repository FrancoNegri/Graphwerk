# 139. `ApprovalStore`: fingerprint-guarded approval tracking

Status: done
Decision: docs/decisions/050-apply-becomes-approval-scoped-commit.md

## Goal

A standalone class that tracks which staged file paths the reviewer has
approved, automatically forgetting an approval when the underlying staged
file changes after being approved.

## Acceptance criteria

- `approve(rel_path)` records the path as approved, stamped with the staged
  file's current `file_fingerprint` (`graphwerk/indexing/walk.py`).
- `is_approved(rel_path)` returns `True` only if the path was approved and
  its current staged-file fingerprint still matches the stamped one; `False`
  otherwise (never approved, unapproved, or file changed since approval).
- `unapprove(rel_path)` removes any approval for the path; a no-op if it
  wasn't approved.
- `approved_paths()` returns the set of currently-approved (fingerprint
  still matching) rel_paths.
- `clear(paths)` removes approval entries for exactly the given paths.
- `clear_all()` removes every approval entry.
- A path approved, then re-approved after its content changes, is treated
  as freshly approved (new fingerprint stamped, `is_approved` true again).

## Likely files

- `graphwerk/approval.py` — new `ApprovalStore` class, constructed with the
  staged root `Path` (needed to stat files for fingerprinting).
- `tests/test_approval.py` — new.

## Out of scope

- Wiring into `bootstrap.py`/`server.py`/`CommitEngine` — ticket 140/141.
- Symbol/hunk-level approval — file paths only.
