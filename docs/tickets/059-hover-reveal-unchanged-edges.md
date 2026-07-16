# 059. Hide unchanged-status edges by default; reveal on node hover

Status: done
Decision: docs/decisions/020-edge-hover-reveal-and-zoom-feel.md

## Goal
When `show-imports`/`show-calls` is on, only edges carrying review signal
(non-`unchanged` `status`) are visible by default; grey/unchanged edges
stay hidden until the user hovers one of their endpoint nodes, then reveal
for just that node's own incident edges.

## Acceptance criteria
- An edge with `status === 'unchanged'` (covers all `imports` edges per
  ADR 016, and the majority of `calls` edges) is not rendered/visible by
  default, whenever its kind's checkbox (`show-imports`/`show-calls`) is
  checked on.
- An edge with any other `status` (leading into modified/added/deleted/
  affected code) remains **always visible**, independent of hover — the
  existing checkbox-gate behavior for these is unchanged.
- Hovering a node (`mouseover`) reveals exactly that node's own incident
  edges (`node.connectedEdges()`), including unchanged-status ones that
  the checkbox already permits; un-hovering (`mouseout`) hides them again
  (re-applying the same status filter).
- Toggling `show-imports`/`show-calls` off still fully removes that edge
  kind — hover cannot reveal an edge kind that's checked off. (I.e. the
  existing kind-level filter in `toElements` runs first; hover-reveal is a
  second filter layered on what that step already lets through.)
- A test/manual check confirms: with `show-calls` on and no hover, only
  colored (non-unchanged) `calls` edges are visible; hovering a node with
  unchanged-status edges shows them; un-hovering hides them again.

## Likely files
- `static/app.js` — edge style/visibility logic (~lines 308-329 for edge
  style rules; add `mouseover`/`mouseout` node listeners near the existing
  `cy.on(...)` handlers ~line 338-346).
- `static/style.css` — if visibility is done via a CSS class rather than a
  Cytoscape style selector, add the hidden/revealed rule here instead.

## Out of scope
- Any change to `show-imports`/`show-calls` checkbox semantics — they
  still gate edge kind, untouched by this ticket.
- One-hop neighbor reveal on hover — only the hovered node's own edges
  reveal (see ADR 020, alternatives considered).
- Persisting hover/reveal state — inherently transient, no persistence
  question here.
