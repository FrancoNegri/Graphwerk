# 026. Snapshot attaches a code view to every node

Status: done
Decision: docs/decisions/007-sidebar-code-view.md

Depends on: tickets 024, 025.

## Goal

Every node in `/api/graph` carries `code` — the highlighted, diff-overlaid
line view — for file nodes and symbol nodes, changed or not.

## Acceptance criteria

- `GraphNode` gains `code: list | None`, included in `to_dict()`.
- `GraphService.snapshot` builds it via `build_code_view`: file nodes from
  `FileChange.base_source`/`staged_source`; symbol nodes from the base and
  staged `SymbolInfo.source` of the qualname-matched pair (the same pair
  `_symbol_diff` diffs — status stays the differ's call, per the
  no-hunk-mapping invariant).
- Unchanged nodes get an all-`ctx` highlighted view; added/deleted nodes
  get all-`add`/all-`del`; nodes with no readable text get `code=None`.
- Existing payload fields (`diff`, `source`, `why`, `layer`, ...) are
  unchanged in this ticket.
- Tests (service-level, over a small base/staged fixture pair) assert: a
  modified symbol node's `code` contains interleaved `del` lines and
  non-empty spans; an unchanged node's `code` is all-`ctx`; an added
  file's nodes are all-`add`.

## Likely files

- `graphwerk/models.py` — `GraphNode.code` + `to_dict`
- `graphwerk/service.py` — build and attach views
- `tests/test_service.py` (or equivalent) — extended

## Out of scope

UI rendering (ticket 027); dropping `source` (ticket 028); on-demand
endpoint (ADR 007 escape hatch, not now).
