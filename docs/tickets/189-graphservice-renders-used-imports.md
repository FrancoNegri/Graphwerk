# 189. `GraphService` renders each leaf symbol's `imports_used` as real statement blocks

Status: ready
Decision: docs/decisions/064-changed-method-code-view-surfaces-its-imports.md

## Goal

Each changed leaf symbol's `GraphNode` in the `/api/graph` payload carries
the actual import-statement text for every name in its `imports_used`
(ticket 188), rendered the same line-view shape `renderCode` already
consumes — so the frontend can show it with zero new rendering logic.

## Acceptance criteria

- `GraphNode` gains a new field (e.g. `used_imports: list | None`) — a list
  of rendered statement blocks (one per distinct statement backing a name
  in `imports_used`; a symbol referencing two names from the same
  statement renders that statement once, not twice).
- Each block reuses `_statement_code_lines` (or an equivalent extracted
  helper) exactly as the calls panel already does for admitting imports
  (ADR 038) — same op/highlight-span shape, so `renderCode` on the
  frontend needs no new branch.
- Populated in `GraphService.snapshot()` at the point each leaf symbol's
  `GraphNode` is built, by resolving `info.imports_used` (from the
  `staged`/`base` `SymbolInfo`, same precedence already used for `info`
  elsewhere in that loop) against the relevant `FileIndex.imported_names`.
- `None`/empty list when `imports_used` is empty (matches how `code`/`diff`
  already use `None` for "nothing here", per `GraphNode.to_dict`'s
  existing convention) — not an empty-but-present list, so the payload
  size doesn't grow for the common case.
- `to_dict()` includes the new field.
- A test against a small fixture file (module-level `import` + a method
  using one of its names) asserts the rendered statement text/line appear
  on that method's node.

## Likely files

- `graphwerk/models.py` — new `GraphNode` field + `to_dict()` entry.
- `graphwerk/service.py` — resolve/attach `used_imports` in `snapshot()`;
  reuse `_statement_code_lines`.
- `tests/` — new snapshot-level test alongside the existing
  admitting-imports/service tests.

## Out of scope

- Frontend rendering of the new field — ticket 190.
- Any change to `via_imports`/`admitting_entry` (the calls-panel
  mechanism) beyond reusing its existing `_statement_code_lines` helper.
