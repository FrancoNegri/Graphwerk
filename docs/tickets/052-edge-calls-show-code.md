# 052. Edge-calls panel renders caller/callee code

Status: done
Decision: docs/decisions/017-edge-calls-show-code.md

## Goal

Clicking a `calls` edge shows the actual code (with diff overlay and
highlighting) of the callers and callees it collapsed, not just their
labels — so reviewing a call relationship doesn't require separately
expanding containers and clicking each symbol node.

## Acceptance criteria

- `showEdgeCalls` collects the unique node ids referenced across the
  edge's `calls` list (source and target of every pair), in first-seen
  order, deduped so a symbol appearing in multiple collapsed pairs
  (e.g. one caller hitting three methods on the same class) renders
  once.
- For each unique id, the edge-calls sidebar section renders a heading
  (reuse `qualifiedLabel`) followed by that node's code via the existing
  `renderCode(node.code)` — the same function the node details panel
  already calls. Skip ids with no `code` (shouldn't happen in practice,
  but don't throw).
- The existing source → target label list stays, unchanged, above the
  new code panels.
- Tapping empty canvas or a node still clears/hides the edge-calls
  section, same as today.
- Manual check: collapse two classes where one calls three different
  methods on the other, with "show calls" on. Click the single rendered
  edge — the sidebar lists all three calls as today, plus one code panel
  for the caller and one for each distinct callee method (not three
  copies of the caller). Click an edge for a single, non-collapsed call
  — sidebar shows the one label plus exactly two code panels (caller,
  callee).

## Likely files

- `static/app.js` — `showEdgeCalls`.
- `static/index.html` — possibly a wrapper element/heading style for the
  new code panels inside `#edge-calls`, if `showEdgeCalls` needs more
  structure than string-concatenating into `#d-calls-list`.

## Out of scope

- Any equivalent code rendering for `imports` edges.
- Side-by-side/dual-column layout for caller vs. callee code.
- Jump-to-node-on-canvas from the edge-calls panel.
