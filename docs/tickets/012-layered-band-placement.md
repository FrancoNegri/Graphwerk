# 012. Layered band placement

Status: done
Decision: docs/decisions/002-graph-layout-legibility.md

## Goal

Files render in horizontal bands by import depth — importers above what
they import — so a change's vertical position shows where in the
architecture it lands, and file boxes stop overlapping.

## Acceptance criteria

- The fcose layout receives constraints built from ticket 011's layers
  (e.g. `relativePlacementConstraint` top/bottom pairs and/or horizontal
  `alignmentConstraint` groups) so that any file in layer N renders
  strictly above any file it imports in layer < N.
- File boxes do not overlap at any collapse state (tune
  `nodeSeparation`/repulsion as needed while wiring constraints).
- Position carry-over across refreshes still works: a poll-driven refetch
  with unchanged topology does not rescramble the map.
- The changed-only and hide-tests views still lay out correctly (layers
  computed from the full graph, applied to whichever files are visible).
- Works on the demo repo and on a real repo (agendabot) without console
  errors.

## Likely files

- `static/app.js` — `layoutOptions()` grows constraint wiring from the
  layer map.

## Out of scope

Manual layer pinning, directory grouping, animation polish, any layout
engine swap.
