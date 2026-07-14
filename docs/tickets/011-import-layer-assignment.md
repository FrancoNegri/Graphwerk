# 011. Import-depth layer assignment

Status: ready
Decision: docs/decisions/002-graph-layout-legibility.md

## Goal

Every file node gets a layer number derived from the import graph, so the
layout can band files by architectural depth.

## Acceptance criteria

- A pure function in `static/app.js` maps the graph payload (nodes +
  `imports` edges, lifted to file level) to `fileId → layer`:
  files importing nothing get layer 0; otherwise
  `layer = 1 + max(layer of imported files)` (longest-path depth).
- Import cycles don't loop or crash: files in a cycle share one layer
  (the cycle is treated as a unit for depth purposes).
- Files with no import edges at all land in layer 0.
- Verifiable from the browser console (the function is exposed like
  `window.cy` is) against the demo graph: the demo's known import chain
  produces strictly increasing layers.

## Likely files

- `static/app.js` — layer-assignment function, no rendering change yet.

## Out of scope

Using the layers in the layout (ticket 012); any backend/API change —
the frontend already receives all edges.
