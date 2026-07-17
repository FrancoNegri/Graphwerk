# 085. Scope call-edge resolution to the caller's file or its actual imports

Status: done
Decision: docs/decisions/034-call-edge-resolution-scoped-to-actual-imports.md

## Goal

`GraphService._add_call_edges` stops wiring a caller to a same-named
symbol in a file the caller neither owns nor imports — killing phantom
edges like `e2e_runner.py::run_e2e_scenario` appearing to call
`conversation.py::_format_history`, an unrelated function it never
references, confirmed live on the agendabot dogfood graph.

## Acceptance criteria

- In `_add_call_edges` (`graphwerk/service.py`), a candidate target is only
  wired if its file is the caller's own file, or a file resolved from the
  caller's relevant tree's imports via `ModuleFileResolver` (the same
  resolver `_add_import_edges` already builds) — applied in addition to,
  not instead of, the existing ADR 032 tree-membership filter.
- "The caller's relevant tree" follows the existing ADR 032 branch: a
  `deleted` caller's imports come from its file's `base` `FileIndex`;
  every other caller's imports come from its file's `staged` `FileIndex`.
- Test: two functions with the same simple name in two different files,
  where the caller's file does not import either — asserts no edge is
  created to the file it doesn't import (regression guard for the exact
  agendabot shape: local call resolves, cross-file same-name decoy does
  not).
- Test: a caller whose file does import the target's file still produces
  the edge (no regression on legitimate cross-file calls).
- Test: a caller calling a same-named symbol defined in its own file still
  produces that edge (no regression on local/same-file calls).
- Existing ADR 032 tests (tree-membership filter) continue to pass
  unchanged.

## Likely files

- `graphwerk/service.py` — `_add_call_edges` (new import-scoping filter),
  possibly hoisting `ModuleFileResolver` construction so it's built once
  and shared with `_add_import_edges` rather than twice per snapshot.
- `tests/test_service.py` — new cases per acceptance criteria above.

## Out of scope

- Wildcard imports / dynamically resolved calls (ADR 034, "Out of scope").
- Relative-import dot-level resolution (ticket 054, separate).
- Symbol-move detection (ADR 032, "Alternatives considered").
- Any change to `_add_import_edges` or ADR 033's import-edge status work.
