# 100. Extractor captures import statement text and line

Status: ready
Decision: docs/decisions/038-admitting-imports-render-as-real-statements.md

## Goal

`FileIndex` records, per imported module, the verbatim source text of the
statement that imports it and the 1-based line it starts on — so downstream
layers can show the real code instead of a reconstructed module name.

## Acceptance criteria

- `FileIndex` (`graphwerk/models.py`) gains
  `import_statements: dict[str, tuple[str, int]]` (module name →
  (statement source text, start line)), default empty.
- `PythonAstExtractor` fills it from the same executable-node walk that
  fills `imports`:
  - `import a, b` maps both `a` and `b` to that statement's text and line.
  - `from pkg.mod import name as alias` maps `pkg.mod` to the full
    statement text, verbatim.
  - A parenthesized multi-line `from pkg import (a,\n    b)` is captured
    whole, newlines included, with the start line of the statement.
  - A module imported by two statements keeps the first statement.
  - Imports inside `if TYPE_CHECKING:` blocks are excluded, matching the
    existing `imports` behavior (ticket 065).
- `FileIndex.imports` behavior is unchanged.
- Tests in `tests/indexing/test_python_ast.py` cover the four capture
  shapes above.

## Likely files

- `graphwerk/models.py` — `FileIndex.import_statements` field.
- `graphwerk/indexing/python_ast.py` — capture text/line alongside
  `_imported_modules`.
- `tests/indexing/test_python_ast.py` — new cases.

## Out of scope

- Any service or frontend change — tickets 101/102.
- Alias resolution semantics — text capture only.
- Relative-import dot-level resolution (ticket 054).
