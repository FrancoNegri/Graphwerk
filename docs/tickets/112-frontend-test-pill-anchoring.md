# 112. Frontend: anchor paired test pills below their file, left edge at center

Status: done
Decision: docs/decisions/041-paired-test-file-placement.md

## Goal

Once the fcose layout settles, every node carrying `paired_file` snaps to a
position directly below its paired file node, left edge at the file's
horizontal center — a post-layout position override, not an fcose
constraint (fcose has no "offset by half the other node's width"
primitive; see ADR 041's alternatives).

## Acceptance criteria

- On `layoutstop` (or equivalent settle point already used for carrying
  positions across rebuilds), every node with `data.pairedFile` set has its
  position set to: x = paired file node's `position('x') + width()/2`,
  y = paired file node's bottom edge + a fixed gap.
- Works for both collapsed (leaf) and expanded (compound) file nodes —
  read the file node's actual rendered `position()`/`width()`/`height()`,
  not a fixed pill size.
- A node's own connected edges (if any survive filtering) still render
  correctly from wherever it's manually positioned — no special-casing
  needed beyond the position set itself.
- Nodes without `paired_file` are untouched by this code path.
- Verified by loading the demo/dogfood graph in a browser and eyeballing
  the result (ADR 005 testing split — no JS test harness).

## Likely files

- `static/app.js` — read `paired_file` from the snapshot payload into node
  data, add the post-layout positioning pass.

## Out of scope

- Horizontal collision/overlap avoidance between a paired column and its
  band neighbors — deferred per ADR 041.
- Any tint or connector-line visual tie — declined per ADR 041.

## Follow-up bug fix

The shipped implementation wired `placePairedTestNodes` to the `layoutstop`
event, but `renderGraph`'s initial layout runs and emits `layoutstop`
synchronously *inside* the `cytoscape({...})` constructor call, before the
`cy.on("layoutstop", ...)` listener a few lines later ever gets registered.
Since `renderGraph` only ever runs one layout pass per rebuild, that
listener never fired — paired test pills stayed wherever fcose's force
layout dropped them. Fixed by calling `placePairedTestNodes()` directly
right after `cy.nodes().updateStyle()` (so width()/height() reads see
resolved label sizes) instead of listening for an event that never fires.
