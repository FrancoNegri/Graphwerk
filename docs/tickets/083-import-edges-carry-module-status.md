# 083. Import edges carry per-module status and the responsible module name

Status: ready
Decision: docs/decisions/033-import-edge-status-and-pertinent-import-inspection.md

## Goal

`GraphEdge` for an `imports`-kind edge reflects the real status of the
specific import that produced it (from ticket 082's `change.imports`)
instead of always defaulting to `unchanged`, and records which module
caused the edge so the UI can name it later (ticket 084). Also fixes the
latent bug where a removed import produces no edge at all.

## Acceptance criteria

- `GraphEdge` (`graphwerk/models.py`) gains `module: str | None = None`,
  included in `to_dict()`. Left `None` for `calls`-kind edges.
- `GraphService._add_import_edges` iterates the union of
  `change.base.imports | change.staged.imports` (not just
  `(change.staged or change.base).imports`), so a removed import still
  produces an edge instead of silently disappearing.
- Each produced `GraphEdge` has `status` set from `change.imports[module]`
  and `module` set to that module name.
- Test: a file that adds an import produces an `imports` edge with
  `status == Status.ADDED` and `module` equal to the added module name.
- Test: a file that removes an import (present in base, gone from staged)
  still produces an `imports` edge, with `status == Status.DELETED` —
  regression guard for the silent-disappearance bug.
- Test: an unchanged import still produces an edge with
  `status == Status.UNCHANGED` (existing behavior preserved).

## Likely files

- `graphwerk/models.py` — `GraphEdge.module` field + `to_dict()`.
- `graphwerk/service.py` — `_add_import_edges`.
- `tests/test_service.py` (or wherever `_add_import_edges` is currently
  covered) — new cases per acceptance criteria above.

## Out of scope

- Frontend rendering/coloring of the new status (ticket 084).
- Extending `_mark_affected` (blast radius) to `imports` edges (ADR 033,
  "Out of scope").
