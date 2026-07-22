# 187. `FileIndex` tracks module-level import name bindings

Status: done
Decision: docs/decisions/064-changed-method-code-view-surfaces-its-imports.md

## Goal

`FileIndex` can answer "what statement bound this name?" for any name bound
by a *module-level* (depth-0) `import`/`from...import` statement in the
file — the missing primitive the rest of ADR 064 attributes per-symbol
import usage against.

## Acceptance criteria

- `FileIndex` gains a new field mapping each module-level bound name to the
  statement that bound it (verbatim source text + 1-based line), e.g.
  `imported_names: dict[str, tuple[str, int]]`.
- `PythonAstExtractor` populates it only from `Import`/`ImportFrom` nodes
  that are direct statements of the module body (or inside a top-level
  `if`/`elif`/`else` per the existing `_iter_symbol_definitions`-style
  descent) — not from imports nested inside any function or class body.
- Binding names follow real Python semantics: `import pkg.sub` binds
  `pkg`; `import pkg.sub as alias` binds `alias`; `from x import y` binds
  `y`; `from x import y as z` binds `z`; a single statement with multiple
  names (`from x import a, b`) binds each separately, both pointing at the
  same statement text/line.
- `from x import *` binds nothing (no test asserts a crash or a spurious
  entry for the wildcard name).
- If the same name is bound by more than one module-level statement (e.g.
  re-imported further down), the later one wins (matches real Python name
  resolution — the last binding is the one in effect at any later use).
- Existing `import_statements`/`imports` fields and their tests are
  unaffected — this is a pure addition.

## Likely files

- `graphwerk/models.py` — new `FileIndex.imported_names` field.
- `graphwerk/indexing/python_ast.py` — populate it during `extract()`.
- `tests/` (wherever `python_ast` extraction is already tested) — new
  cases for aliasing, multi-name imports, nested-vs-module-level imports,
  and wildcard imports.

## Out of scope

- Anything that *consumes* this table (per-symbol attribution, rendering)
  — that's ticket 188/189.
- Nested/local import binding tracking — deliberately excluded (ADR 064:
  "Imports bound only inside a different function/method... genuinely out
  of scope").
