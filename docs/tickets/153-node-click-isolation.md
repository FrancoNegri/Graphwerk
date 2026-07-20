# 153. Node click isolates its edge-neighborhood

Status: ready
Decision: docs/decisions/056-node-click-isolates-neighbors.md

## Goal
Tapping a node hides every other node that isn't structurally required
around it or directly connected to it by an edge, so the reviewer sees
just that node's neighborhood; tapping empty canvas (or a different node)
restores/recomputes the view.

## Acceptance criteria
- Define the keep set for a tapped node `S`: `S` itself; `S`'s compound
  ancestors (parent chain); `S`'s descendants (if `S` is an expanded
  container); every node joined to `S` by a `calls` or `imports` edge
  currently in the Cytoscape instance (regardless of that edge's own
  hover/pinned/unchanged display state); and those neighbors' own compound
  ancestors.
- Every node in `cy.nodes()` outside the keep set gets hidden (a new CSS
  class + `display: none` rule in the Cytoscape style array, mirroring how
  `edge.revealed`/`edge.pinned` already work ~`static/app.js:460`) —
  nothing is removed from the graph, so it's trivially reversible.
- Tapping a different node recomputes the keep set from scratch for the
  new selection (previously-hidden nodes can become visible again;
  previously-visible ones can become hidden).
- Tapping empty canvas (existing `cy.on("tap", ...)` handler ~`static/
  app.js:483`) restores every node to visible, alongside the existing
  `clearDetails()`/`unpinAllEdges()` reset.
- The hidden/kept state is reapplied after a `renderGraph()` rebuild (e.g.
  a poll-triggered refresh while a node is still selected) — mirroring how
  `applyPinnedEdges()` (~`static/app.js:313`) already reapplies pinned-edge
  state after `renderGraph()` destroys and recreates `cy`.
- Manually verified in the browser (per CLAUDE.md — this is a Cytoscape
  interaction, not something `curl`/API checks cover): click a node with
  both connected and unrelated nodes on screen and confirm only the
  neighborhood stays visible; click empty canvas and confirm everything
  reappears; click a different node and confirm the isolation follows it.

## Likely files
- `static/app.js` — new `isolatedNodeId` state (alongside `selectedId` /
  `pinnedEdgeIds`), a keep-set/`applyNodeIsolation()` function, wiring into
  the node-tap handler (~line 475), the empty-canvas-tap handler (~line
  483), and the end of `renderGraph()` (~line 492, alongside
  `applyPinnedEdges()`), plus the new style-array rule (~line 460).

## Out of scope
- Preventing an edge tap from clearing the underlying Cytoscape node
  selection state — ticket 154.
- Any toggle/indicator UI for this behavior (ADR 056, out of scope).
- Hiding a visible neighbor's own unconnected descendants (ADR 056, out of
  scope).
