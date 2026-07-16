# 062. Render layer 0 at the top of the graph

Status: done
Decision: docs/decisions/022-entry-points-anchor-top-layer.md
Depends on: docs/tickets/061-layer-from-entry-points.md

## Goal

After ticket 061 makes layer 0 mean "entry point" instead of "leaf," the
UI's placement constraints put layer 0 at the top and increasing layer
numbers step downward, matching the new backend semantics.

## Acceptance criteria

- `appendBandConstraints`'s layer ordering (`layersDeepestFirst` in
  `static/app.js`) sorts ascending instead of descending, so the smallest
  layer number anchors the top-most band.
- The adjacent comment ("Deeper layers (entry points, callers) render
  above what they depend on") is corrected to describe the new direction
  (layer 0 — entry points/callers — render above what they depend on).
- Manual check in the browser (per CLAUDE.md — this is a feel/placement
  change, not covered by curl): serve the agendabot dogfood pair, confirm
  `webhook.py`, `trace/__main__.py`, and other files nothing imports all
  render in the same top band; leaf utility files render at the bottom.
- The per-file function-call bands (`functionAnchorsByLayerPerFile`)
  follow the same top-down convention automatically, since they reuse the
  same `appendBandConstraints` helper — confirm by eyeballing a file with
  a multi-level call chain expanded.

## Likely files

- `static/app.js` — `appendBandConstraints`'s sort comparator and its
  adjacent comment.

## Out of scope

- Any change to spacing/gap constants, left-right barycenter ordering, or
  the directory-grouping re-sort — unaffected by which end is "up" (ADR
  022).
- The layer computation itself (ticket 061) — this ticket only changes
  which end of the existing numbers renders at the top.
