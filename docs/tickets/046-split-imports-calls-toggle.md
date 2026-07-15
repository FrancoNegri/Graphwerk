# 046. Split "show deps + calls" into independent imports/calls toggles

Status: done
Decision: docs/decisions/014-split-imports-calls-toggle.md

## Goal

Let a reviewer show `calls` edges without `imports` edges (or vice versa),
replacing the single combined checkbox from ticket 044.

## Acceptance criteria

- `static/index.html`'s single `show-edges` checkbox is replaced by two
  checkboxes, `show-imports` and `show-calls`, both unchecked by default.
- `static/app.js` replaces `showEdgesView` with `showImportsView` and
  `showCallsView` (both default `false`), each with its own setter
  (`setShowImportsView` / `setShowCallsView`) that re-renders from the held
  `graphData`, matching `setChangedOnlyView` / `setHideTestsView`.
- `toElements` includes an `imports` edge iff `showImportsView` is `true`
  and a `calls` edge iff `showCallsView` is `true`; the two are independent
  (either can be on with the other off). Node elements are never filtered
  by this toggle.
- Manual check: load the demo graph, confirm no import/call edges render by
  default; checking only "show calls" reveals solid `calls` edges without
  dashed `imports` edges; checking only "show imports" does the reverse;
  checking both shows both.

## Likely files

- `static/index.html` — replace the one checkbox with two.
- `static/app.js` — replace `showEdgesView`/`setShowEdgesView` with the two
  independent booleans/setters, split the edge filter in `toElements`,
  update event listener registration.

## Out of scope

- Persisting toggle state across reloads (ADR 014, out of scope).
- Any server/`GraphEdge` model change — edges already carry `kind`.
