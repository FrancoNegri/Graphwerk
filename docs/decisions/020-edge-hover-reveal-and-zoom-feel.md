# 020. Hide unchanged edges behind hover reveal; tune wheel-zoom feel

Status: proposed
Date: 2026-07-16

## Context

Two small interaction-polish requests against the current graph view, both
scoped to `static/app.js` (Cytoscape), both under Phase 2's "Scale UX ...
so big repos open readable" line rather than a detour:

1. **Wheel zoom feels off.** `wheelSensitivity` is set to `0.3`
   (`static/app.js:236`) with no `minZoom`/`maxZoom` bounds, so it's easy
   to overshoot — zoom out past the point the graph is legible, or zoom in
   past the point a node's contents are useful. Pure config tuning; no
   real alternatives to weigh, no invariant touched.

2. **Unchanged edges add clutter that survives the existing toggles.**
   ADR 013 added `show-imports`/`show-calls` checkboxes (imports off,
   calls on by default per ADR 015) to gate whether a whole edge *kind*
   renders. ADR 016 then gave `calls` edges a `status` field so
   review-relevant edges (leading into changed/affected code) render in
   status color while the rest render grey/unchanged. In practice, most
   edges in any repo are the grey/unchanged kind — turning `show-calls` on
   floods the view with structural edges that aren't part of the change
   being reviewed, which is exactly the legibility problem ADR 013/015
   were already chasing, just one layer down (kind-level filtering wasn't
   enough; status-level filtering is the next cut).

   This modifies the mechanism ADR 013/015 established, so it's a
   north-star decision rather than a quick fix, even though the diff is
   small.

## Decision

**Wheel zoom (`static/app.js`, `cytoscape(...)` config, ~line 236):**
- Lower `wheelSensitivity` further (empirically tuned during
  implementation — start around `0.15`–`0.2`) so a single wheel notch
  moves less.
- Add explicit `minZoom`/`maxZoom` bounds so scrolling can't push the
  graph into an unreadable speck or a single-node blowup.

**Edge hover reveal (`static/app.js`, `static/style.css`):**
- Edges with `status === 'unchanged'` (this already covers `imports`
  edges, which are always unchanged per ADR 016, and the majority-case
  `calls` edges) render hidden by default whenever their kind's checkbox
  is on.
- Hovering a node (`cy.on('mouseover'/'mouseout', 'node', ...)`) reveals
  exactly that node's own incident edges — source or target — for the
  duration of the hover, regardless of status. No one-hop-further
  neighbor expansion (keeps the reveal predictable and cheap: a direct
  `node.connectedEdges()` selector, not a graph walk).
- Edges with a non-unchanged `status` (the actual review signal — leading
  into modified/added/deleted/affected code) stay **always visible**,
  hover or not. This is what ADR 016's status coloring exists to surface;
  hiding it behind hover would cut against "blast radius for humans"
  (docs/02) as the default view.
- The existing `show-imports`/`show-calls` checkboxes are unchanged in
  meaning: they still gate whether a whole edge kind is considered at all.
  Hover-reveal is a filter applied *within* whatever a checkbox already
  lets through — checked-off edges stay fully absent, hover or not.

## Alternatives considered

- **Replace the checkboxes with hover-only reveal for all edges** —
  fewer controls, but would also hide changed-status edges until hover,
  contradicting ADR 016's "always show the review signal" reasoning.
  Rejected.
- **Reveal one hop of neighbors on hover, not just the hovered node's own
  edges** — more context per hover, but reintroduces the clutter this
  decision exists to remove, and needs a graph walk instead of Cytoscape's
  built-in `connectedEdges()`. Rejected; can revisit if a tight hover
  proves insufficient in practice.
- **Dim (opacity) instead of hide** — already rejected once in ADR 013
  for not solving clutter, same reasoning applies to the status-level cut.
  Rejected.

## Consequences

- Default view (with `show-calls` on) becomes readable at a glance: only
  colored, review-relevant edges are visible without interaction; grey
  structural edges are there on demand via hover.
- No server or model change — `GraphEdge.status` already exists (ADR 016);
  this is purely a client-side display filter, same category as the
  existing toggles. Consistent with ADR 005 (JS stays thin/presentation
  layer only).
- Two more pieces of edge-visibility state layered onto `static/app.js`
  (checkbox kind-gate, now status-gate-plus-hover) — still all client-side
  view state, no new invariant risk, but worth keeping in mind if a third
  layer gets proposed later; may be worth consolidating into one visibility
  predicate at that point.

## Out of scope

- Persisting zoom level or hover state across reloads — no existing toggle
  persists either (ADR 013/015 precedent).
- Touch/pinch-zoom feel — this repo's UI is desktop/mouse-first today;
  revisit only if touch use becomes a real scenario.
- Extending hover-reveal to node visibility/collapse state — this decision
  is edges only; collapse behavior (ADR 015) is untouched.
