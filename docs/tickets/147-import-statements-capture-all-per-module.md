# 147. `FileIndex.import_statements` captures every statement per module

Status: done
Decision: docs/decisions/052-import-statement-attribution-scoped-to-caller.md

## Goal

Stop discarding all but the first import statement per module, so a later
caller-scoped lookup (ticket 148) has the full set to choose from.

## Acceptance criteria

- `FileIndex.import_statements` (`graphwerk/models.py:38`) is
  `dict[str, list[tuple[str, int]]]` — module name → every
  (verbatim statement text, 1-based start line) pair found for that
  module, in file order (was: single tuple, first-wins).
- The extractor (`graphwerk/indexing/python_ast.py:38`, currently
  `index.import_statements.setdefault(module, (statement, node.lineno))`)
  appends every occurrence instead of setting only the first.
- A file with the same module imported at module scope once and inside
  two different functions locally indexes three entries for that module,
  in source order.
- A file with a module imported exactly once still indexes a one-element
  list (existing single-import behavior degrades cleanly).

## Likely files

- `graphwerk/models.py` — `FileIndex.import_statements` type change.
- `graphwerk/indexing/python_ast.py` — extractor appends instead of
  `setdefault`.
- `tests/indexing/` or `tests/test_models.py` (wherever `import_statements`
  is currently covered) — update existing assertions for the new shape,
  add a case with a module imported at multiple scopes.

## Out of scope

- Any caller-scoped selection logic (which entry a given admitting-import
  lookup should use) — ticket 148, `graphwerk/service.py`.
- Any frontend change — this ticket is index-shape only.
