# 180. Module-level and class-level variable symbol extraction

Status: done
Decision: docs/decisions/062-variable-symbols-and-changed-method-blast-radius.md

## Goal

`PythonAstExtractor` extracts simple-name module-level globals and
class-level attributes as `SymbolInfo(kind="variable")` entries, so they
flow through the existing symbol-diffing/node-emission pipeline exactly
like functions and methods already do.

## Acceptance criteria

- A top-level `Assign`/`AnnAssign`/`AugAssign` statement with a single
  `Name` target (e.g. `_CACHE = {}`, `TIMEOUT: int = 30`) produces
  `index.symbols["_CACHE"]` / `index.symbols["TIMEOUT"]` with
  `kind="variable"`, correct `lineno`/`end_lineno`/`source` (the statement
  text).
- An `Assign`/`AnnAssign` directly in a class body (not inside a method)
  produces `index.symbols["ClassName.attr"]` with `kind="variable"`,
  following the same qualname convention methods already use.
- Assignment targets that aren't a single simple `Name` — attribute
  targets (`self.x = 1`), subscript targets (`d["k"] = 1`), tuple/list
  unpacking (`a, b = 1, 2`) — are skipped entirely (produce no symbol),
  at both module and class level.
- An assignment inside a function or method body (module-level or
  nested) does not produce a variable symbol — only statements directly
  in the module body or directly in a class body count.
- Existing class/function/method extraction and all existing tests in
  `tests/test_python_ast.py` (or wherever extractor tests live) continue
  to pass unmodified.

## Likely files

- `graphwerk/indexing/python_ast.py` — add variable-target extraction,
  called from the same top-level/class-body walk that already handles
  `ClassDef`/`FunctionDef`.
- `tests/test_python_ast.py` (exact path may differ — check the repo) —
  new tests for module-level and class-level variable extraction, and the
  skip cases above.

## Out of scope

- `SymbolInfo.uses` / reference tracking from function bodies back to
  these variables — ticket 181.
- Any change to `graphwerk/staging/differ.py`, `graphwerk/service.py`, or
  the frontend — this ticket only makes the symbols extractable; the
  differ/service already handle arbitrary `kind` values generically.
- Instance attributes (`self.x = ...`) — explicitly out of scope per ADR
  062.
