# 148. Admitting-import entry picks the statement scoped to its caller

Status: done
Decision: docs/decisions/052-import-statement-attribution-scoped-to-caller.md

## Goal

Use the full per-module statement list (ticket 147) so `admitting_entry`
picks the statement that actually applies to the caller being rendered,
instead of always the first one indexed for that module — fixing both the
wrong statement text and the false-negative `in_caller_code` this caused
on the agendabot dogfood graph (`TestAdapterResets._call` →
`_apply_adapter_resets`).

## Acceptance criteria

- `admitting_entry` (`graphwerk/service.py:231`) takes the module's full
  statement list and, when `caller_symbol` is given, picks the first
  statement whose start line falls inside `caller_symbol.lineno` ..
  `caller_symbol.end_lineno` (reusing `_statement_in_caller_span`'s
  existing containment check); if none match, falls back to the list's
  first statement (today's behavior).
- `_statement_in_caller_span` and `_statement_code_lines` (or their
  call sites) are updated for the list shape without changing their
  containment semantics.
- When `caller_symbol` is `None` (multi-hop chain hops resolved in a
  different file — `import_chain`'s later hops), behavior is unchanged:
  first statement in the list.
- Regression case from the live dogfood graph: for the agendabot pair
  `tests/test_webhook.py::TestAdapterResets._call` →
  `src/agendabot/conversation.py::_apply_adapter_resets`, the
  `agendabot.webhook` admitting entry resolves to the statement at
  `_call`'s own line 717 (`from agendabot.webhook import
  _apply_adapter_resets`), not line 18's module-level import, and its
  `in_caller_code` is `true` (so the frontend suppresses it, per ADR
  039) — leaving only the legitimate `agendabot.conversation` chain-hop
  entry alongside the caller/callee code sections.
- A caller whose admitting import is only ever at module scope (the
  common case, unaffected by this bug) continues to resolve and render
  identically to today.

## Likely files

- `graphwerk/service.py` — `admitting_entry`, `_statement_in_caller_span`,
  `_statement_code_lines`.
- `tests/test_service.py` (or wherever `_add_call_edges`/`via_imports` is
  covered) — a fixture with two callers in the same file, each with their
  own local import of the same module (mirroring the
  `test_webhook.py` shape), asserting each caller's admitting entry picks
  its own statement.

## Out of scope

- `FileIndex.import_statements` shape change — ticket 147, already done.
- Full Python scope-shadowing resolution — span containment is a
  heuristic per ADR 052; not handled here.
