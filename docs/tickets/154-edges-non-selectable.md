# 154. Edges become non-selectable so clicking one doesn't clear the selected node

Status: ready
Decision: docs/decisions/056-node-click-isolates-neighbors.md

## Goal
Clicking an edge (e.g. to open its edge-calls/edge-imports panel) must not
undo a prior node selection — including the node-click isolation from
ticket 153 — because Cytoscape's default single-selection model otherwise
deselects the previously-tapped node the moment any other selectable
element is tapped.

## Acceptance criteria
- Edges are configured `selectable: false` (element data default or style
  rule in the `cytoscape(...)` config, `static/app.js`).
- Confirm nothing else keys off `edge:selected` (only `node:selected`
  exists today, ~`static/app.js:461`) — grep before/after to make sure this
  doesn't silently break an existing style rule.
- Manually verified in the browser: select a node (with ticket 153's
  isolation active), then tap one of its still-visible edges — the node
  stays visually selected (`node:selected` border) and the isolated view
  does not reset; the edge's own click behavior (`pinEdges`,
  `showEdgeCalls`/`showEdgeImports`) still fires as before.

## Likely files
- `static/app.js` — the `cytoscape(...)` element/style config (edge style
  selector ~line 427, or the `elements`/edge data construction in
  `toElements()` ~line 160-168).

## Out of scope
- The isolation/keep-set logic itself — ticket 153.
- Any change to node selectability or Cytoscape's `selectionType`.
