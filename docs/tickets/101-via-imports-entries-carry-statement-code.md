# 101. `via_imports` entries carry the statement as code lines

Status: done
Decision: docs/decisions/038-admitting-imports-render-as-real-statements.md

## Goal

Each `via_imports` entry on a cross-file `calls` edge carries a `code`
field: the admitting import statement rendered in the code-view line shape
(`{"text", "op", "line", "spans"}`) the panel already consumes, so the
frontend can reuse `renderCode` with zero new logic.

## Acceptance criteria

- `via_imports_entries` (`graphwerk/service.py`) adds `"code"` to each
  entry, built from the caller's relevant tree's
  `FileIndex.import_statements[module]` (ADR 032 branch: base index for a
  `deleted` caller, staged otherwise):
  - one line dict per source line of the statement,
  - `line` numbers starting at the captured start line and incrementing,
  - `spans` from `highlight_lines` over the statement text,
  - `op` mapped from the module's status: `added` → `"add"`, `deleted` →
    `"del"`, anything else → `"ctx"`.
- The entry keeps `module` and `status` unchanged; `code` is `None` when
  the index has no statement for the module.
- Test: added staged-only import → entry `code` is one line with
  `op == "add"`, the statement's real line number, and non-empty `spans`.
- Test: deleted caller → entry `code` text comes from the base tree's
  statement with `op == "del"`.
- Test: import present in both trees → `op == "ctx"`.
- Existing ticket 090 `via_imports` tests pass with the added field (adjust
  equality assertions only as needed).

## Likely files

- `graphwerk/service.py` — `via_imports_entries` builds the code lines.
- `tests/test_service.py` — cases above.

## Out of scope

- Frontend rendering — ticket 102.
- The imports-edge panel payload (`_add_import_edges`) — untouched.
