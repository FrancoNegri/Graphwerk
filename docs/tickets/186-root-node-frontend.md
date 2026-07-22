# 186. Frontend: render the `Root` node

Status: done
Decision: docs/decisions/063-root-entry-point-node.md

## Goal

The `Root` node (ticket 185, once present in the `/api/graph` payload)
renders as a visually distinct anchor above the entry-point file band,
always visible, with a minimal detail panel.

## Acceptance criteria

- `node[kind='root']` gets a distinct shape (e.g. diamond) with no status
  border/fill tint (it has no status), clearly different from `file`/
  `class`/`function`/`method`/`variable` nodes.
- `edge[kind='entrypoint']` renders thin/dashed, visually distinct from
  `imports`/`calls`/`uses` edges, and is **not** gated behind any
  visibility toggle — always shown when the graph has a `Root` node.
- `Root` sits above the layer-0 file band in the rendered layout (verify
  via the existing `layeredPlacementConstraints`/`appendBandConstraints`
  machinery in `static/app.js`, which should need no changes since `-1`
  already sorts before `0` in the existing ascending comparator — confirm
  this holds, fix only if it doesn't).
- Selecting the `Root` node shows a minimal detail panel: its label and a
  short static description (no status chip, no why/code/diff sections —
  those sections stay hidden the way they already do for nodes with no
  such data).
- `Root` is excluded from collapse/expand interactions (it has no
  file/class semantics to collapse) and from the "changed + blast radius
  only" filter (it should remain visible regardless of that toggle's
  state, since it carries no change/blast-radius status of its own).

## Likely files

- `static/app.js` — Cytoscape style rules, node-detail rendering
  (`showDetails` or equivalent), any filter logic that needs to special-case
  `kind='root'`.
- `static/style.css` — if styling lives there rather than inline.

## Out of scope

- Backend changes — this ticket only consumes the payload ticket 185
  produces.
