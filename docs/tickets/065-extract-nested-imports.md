# 065. Collect imports from the whole file, skipping TYPE_CHECKING blocks

Status: done
Decision: docs/decisions/024-extract-nested-imports.md

## Goal

`PythonAstExtractor.extract` finds a module's imports wherever they appear
in the file (module top level, inside a function, inside a class method) —
not just `tree.body` — so a file reached only through a lazy/deferred
import gets a real edge into it, while an import that only exists behind
`if TYPE_CHECKING:` still doesn't count (it never executes).

## Acceptance criteria

- A function-local import (`def f(): from pkg.mod import Thing`) is
  collected into `FileIndex.imports`, same as a top-level one.
- An import nested inside a method, and one nested inside a nested function,
  are both collected (walks the full tree, not just one level deep).
- An import inside `if TYPE_CHECKING:` (guarded by `from typing import
  TYPE_CHECKING` or `import typing` + `typing.TYPE_CHECKING`) is **not**
  collected, mirroring `executor.py`'s real pattern in the agendabot dogfood
  repo (`if TYPE_CHECKING: from agendabot.calendar.port import
  CalendarPort`).
- An import inside a plain `if some_other_condition:` (not `TYPE_CHECKING`)
  at module level is still collected — only the `TYPE_CHECKING` name is
  special-cased, not `if` blocks generally.
- Existing top-level-import tests in `tests/test_python_ast.py` (or
  wherever `PythonAstExtractor` is tested) still pass unmodified.
- Symbol extraction (functions/classes/methods) is unchanged — still
  `tree.body`-scoped; only import collection widens.

## Likely files

- `graphwerk/indexing/python_ast.py` — `PythonAstExtractor.extract`,
  `_imported_modules`.
- `tests/test_python_ast.py` (or equivalent existing extractor test file) —
  new nested-import and `TYPE_CHECKING`-exclusion cases.

## Out of scope

- `try`/`except ImportError` handling — already covered by a plain
  whole-tree walk, no special-casing needed (ADR 024).
- Any change to `_called_names`, `FileIndex`/`SymbolInfo` shape, or
  anything in `graphwerk/layout.py` — this ticket only fixes what
  `index.imports` contains; ADR 023's layering fixes consume it unchanged.
