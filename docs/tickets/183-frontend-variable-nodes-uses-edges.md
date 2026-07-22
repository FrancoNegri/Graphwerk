# 183. Frontend: render `variable` nodes and `uses` edges

Status: done
Decision: docs/decisions/062-variable-symbols-and-changed-method-blast-radius.md

## Goal

`variable`-kind nodes and `uses`-kind edges (tickets 180-182, already
present in the `/api/graph` payload once those land) render on the graph,
nested/styled consistently with existing node/edge conventions, with
`uses` gated behind its own default-hidden visibility toggle like
`calls`/`imports` already are (ADR 013).

## Acceptance criteria

- A `variable` node renders nested inside its parent (file for
  module-level, class for class-level) the same way `method` nodes
  already nest inside their class — no layer/order needed (matches
  today's `method` treatment), status-colored the same way every other
  node already is.
- A `uses` edge renders with its own distinct style (distinguishable from
  `calls`/`imports` at a glance) and is hidden by default, behind a new
  checkbox alongside the existing calls/imports toggles.
- Toggling the new checkbox shows/hides `uses` edges without affecting
  `calls`/`imports` visibility, consistent with `static/app.js`'s existing
  independent per-kind toggle logic.
- Selecting a `variable` node shows its status/diff/code the same way
  selecting any other symbol node already does — no new special-casing
  needed if the existing generic node-detail path already handles
  arbitrary `kind` values; verify and fix only if it doesn't.
- Double-clicking a class or file with `variable` children collapses them
  along with methods, consistent with existing collapse behavior.

## Likely files

- `static/app.js` — node/edge style rules (`toElements`, the `style:
  [...]` block in `renderGraph`), new toggle wiring.
- `static/index.html` — new checkbox for the `uses` edge toggle.
- `static/style.css` — if any dedicated styling lives there rather than
  inline in `app.js`'s Cytoscape style block.

## Out of scope

- The sidebar "Affects" summary line — ticket 184.
- Any backend change — this ticket only consumes payload fields ADR 062's
  earlier tickets already produce.
