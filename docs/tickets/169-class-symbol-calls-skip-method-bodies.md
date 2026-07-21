# 169. Class symbol `calls` should skip method bodies

Status: done
Decision: docs/decisions/059-class-symbol-calls-exclude-method-bodies.md

## Goal

A class's own `SymbolInfo.calls` no longer includes calls made inside its
methods, so the graph stops emitting a redundant class-level `calls` edge
that duplicates a signal its method's own edge already carries.

## Acceptance criteria

- `PythonAstExtractor.extract`'s class-kind `SymbolInfo.calls` contains
  only names called directly in the class body (e.g. a class attribute
  default calling a factory function), not names called inside any
  `FunctionDef`/`AsyncFunctionDef` nested in that class.
- A method's own `SymbolInfo.calls` is unaffected — still every call in
  its full body, exactly as today.
- New test: a class with a method that calls something produces exactly
  one `calls` edge (from the method, not the class) to that target in
  `GraphService.snapshot()` — regression guard for the dogfood report
  (`TestOnlyRouter` / `TestOnlyRouter.__init__` both edging to
  `get_calendar`).
- New test: a genuine class-body-level call (outside any method) is still
  captured on the class symbol's `calls`.

## Likely files

- `graphwerk/indexing/python_ast.py` — a scoped variant of
  `_called_names` for class symbols that doesn't descend into nested
  `FunctionDef`/`AsyncFunctionDef` bodies.
- `tests/indexing/test_python_ast.py` — extractor-level coverage for the
  scoped class `calls` set.
- `tests/test_service.py` — the end-to-end regression test for the
  duplicate-edge dogfood report.

## Out of scope

- Any change to `static/app.js`'s edge-collapsing/aggregation logic (ADR
  016/055) — unaffected, becomes the sole correct source for "this
  collapsed class calls X" once the backend stops double-emitting.
- Dedup logic in `service.py` — rejected alternative, see ADR 059.
