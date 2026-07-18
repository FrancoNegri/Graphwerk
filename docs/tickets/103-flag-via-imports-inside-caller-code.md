# 103. `via_imports` entries flag statements inside the caller's own code

Status: done
Decision: docs/decisions/039-admitting-imports-inline-in-call-pair.md

## Goal

Each `via_imports` entry says whether its import statement already sits
inside the caller symbol's own line span, so the frontend can skip
rendering a statement the caller's code block will show anyway (nested
imports, ticket 065).

## Acceptance criteria

- Every `via_imports` entry gains `"in_caller_code": bool`.
- `True` exactly when the statement's captured start line falls within
  the caller symbol's `lineno`..`end_lineno` in the caller's relevant
  index (base for a deleted caller, staged otherwise — the ADR 032
  branch `via_imports_entries` already takes).
- `False` when the statement sits outside the caller's span (the normal
  top-of-file import), when no statement text was captured, or when the
  caller id has no matching symbol in that index.
- Existing `via_imports` tests still pass with the new field present.

## Likely files

- `graphwerk/service.py` — `via_imports_entries` gains the containment
  check; the call site at `_add_call_edges` passes the caller's symbol
  (it already has `source_id` and the relevant index in scope).
- `tests/test_service.py` (or wherever ticket 090's tests live) — new
  cases: top-of-file import → `False`; import nested inside the calling
  function → `True`; deleted-caller branch resolves the span in base.

## Out of scope

- Any frontend change — ticket 104.
- Changing which entries are produced or their `module`/`status`/`code`
  fields.
