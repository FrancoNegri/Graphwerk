# 015. Layered placement for symbols within an expanded file

Status: ready
Decision: docs/decisions/003-symbol-layered-placement.md

## Goal

When a file is expanded, its top-level functions render in horizontal bands
by call depth (ticket 014's layers) instead of fcose's organic placement,
the symbol-level analogue of ticket 012.

## Acceptance criteria

- `layoutOptions()`/`layeredPlacementConstraints()` add alignment and
  relative-placement constraints per expanded file, derived from ticket
  014's `symbolLayersByCallDepth`, using the same simple-anchor approach
  ticket 012 used for compound file nodes.
- Functions sharing a layer get a minimum horizontal gap of 190 (matching
  the constant used for same-layer files).
- Cross-layer vertical gap is smaller than the 220 used between file bands
  (function chips are smaller than file boxes) — pick a value consistent
  with the existing `nodeSeparation: 75` default.
- A file with only one layer of functions (no calls among them) triggers no
  new constraints for that file (mirrors the `anchorsByLayer.size < 2`
  early-out at the file level).
- Verifiable from the browser console / visually in the demo graph: expand
  a file with a call chain among its functions and confirm they stack in
  bands top-to-bottom by caller-to-callee order.

## Likely files

- `static/app.js` — extend `layeredPlacementConstraints()`.

## Out of scope

Methods inside classes, class-vs-class layering; persisting layout state.
