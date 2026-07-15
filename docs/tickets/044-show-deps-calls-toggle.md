# 044. "show deps + calls" edge visibility toggle

Status: done
Decision: docs/decisions/013-graph-edge-visibility-toggle.md

## Goal

Hide `imports`/`calls` edges by default so the graph reads clearly out of
the box, with a one-click way to bring them back.

## Acceptance criteria

- A new checkbox "show deps + calls" in `static/index.html`, unchecked by
  default, alongside `changed-only` and `hide-tests`.
- `static/app.js` tracks a `showEdgesView` boolean (default `false`); its
  change handler calls a `setShowEdgesView(enabled)` setter that re-renders
  from the held `graphData`, matching `setChangedOnlyView` /
  `setHideTestsView`.
- `toElements` (or wherever edges are built into Cytoscape elements) omits
  edges whose `kind` is `imports` or `calls` when `showEdgesView` is
  `false`; includes them when `true`. Node elements are never filtered by
  this toggle.
- Manual check: load the demo graph, confirm no import/call edges render
  until the box is checked, and both edge kinds (dashed `imports`, solid
  `calls`) appear once it is.

## Likely files

- `static/index.html` — new checkbox markup.
- `static/app.js` — `showEdgesView` state, `setShowEdgesView`, edge
  filtering in element-building, event listener registration.

## Out of scope

- Splitting into independent imports/calls toggles (ADR 013, Out of
  scope).
- Persisting the toggle across reloads.
- Any server/`GraphEdge` model change — edges already carry `kind`.
