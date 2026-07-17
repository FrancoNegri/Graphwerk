# 090. Call edges carry the imports that admit them

Status: ready
Decision: docs/decisions/035-calls-panel-surfaces-admitting-imports.md

## Goal

Every cross-file `calls` edge in the snapshot names the import module(s)
that make the call reachable, with each module's own status — so the UI
can show "this call is backed by this (added/unchanged/deleted) import"
without re-deriving anything client-side.

## Acceptance criteria

- `GraphEdge` (`graphwerk/models.py`) gains `via_imports: list | None`,
  serialized by `to_dict()`. Each entry carries a module name and that
  module's status (from `change.imports`, ticket 082) in whatever shape
  `to_dict()` emits for the frontend (e.g. `[{"module": ..., "status":
  ...}]`).
- In `_add_call_edges` (`graphwerk/service.py`), a cross-file `calls`
  edge's `via_imports` lists exactly the module(s) from the caller's
  relevant tree's imports whose `ModuleFileResolver` resolution equals
  the target's file — the same resolution the ADR 034 filter already
  performs. "Relevant tree" follows the existing ADR 032 branch (base
  for a `deleted` caller, staged otherwise).
- A same-file `calls` edge and every `imports`-kind edge have
  `via_imports` as `None`.
- Test: caller in file A calls a symbol in file B, where A's staged tree
  imports B's module and that import is staged-only — the edge's
  `via_imports` names the module with status `added`.
- Test: same shape but the import exists in both trees — status
  `unchanged`.
- Test: a same-file call produces `via_imports` of `None`.
- Test: a `deleted` caller's edge derives `via_imports` from its file's
  base imports (mirroring the existing ADR 032/034 deleted-caller
  tests).
- Existing ticket 081/085 call-edge tests pass unchanged.

## Likely files

- `graphwerk/models.py` — `GraphEdge.via_imports` + `to_dict`.
- `graphwerk/service.py` — `_add_call_edges` records admitting modules
  (it already resolves them; keep instead of discard).
- `tests/test_service.py` (and `tests/test_models.py` if edge
  serialization is covered there) — cases above.

## Out of scope

- Any frontend change — ticket 091.
- Changes to `_add_import_edges` or the imports-edge `module` field.
- Relative-import dot-level resolution (ticket 054).
