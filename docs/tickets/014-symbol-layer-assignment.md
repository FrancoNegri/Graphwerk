# 014. Call-depth layer assignment for symbols within a file

Status: done
Decision: docs/decisions/003-symbol-layered-placement.md

> Superseded by [ADR 005](../decisions/005-server-side-layers.md): the JS
> `symbolLayersByCallDepth` this ticket added was replaced by server-side
> layer assignment in `graphwerk/layout.py`, exposed as `node.layer` in the
> payload and covered by `tests/test_layout.py`. The console-verifiability
> criterion no longer applies.

## Goal

Every top-level function symbol gets a layer number derived from intra-file
call edges, the symbol-level analogue of ticket 011's
`fileLayersByImportDepth`, so the layout can band a file's own functions by
call depth once it's expanded.

## Acceptance criteria

- A pure function in `static/app.js` maps the graph payload (nodes +
  `calls` edges) plus a file id to `symbolId → layer`, scoped to that
  file's own top-level function children: functions calling nothing (within
  the file) get layer 0; otherwise `layer = 1 + max(layer of callees within
  the file)` (longest-path depth). Cross-file call edges are ignored for
  this computation.
- Recursive calls — a function calling itself, or a cycle between two or
  more functions in the same file — don't loop or crash: every function in
  the cycle shares one layer, using the same SCC approach ticket 011 used
  for import cycles (reuse `stronglyConnectedComponents` rather than
  reimplementing it).
- Functions with no intra-file call edges at all land in layer 0.
- Verifiable from the browser console (exposed on `window`, like
  `fileLayersByImportDepth`) against the demo graph: pick a file with a
  known call chain and confirm strictly increasing layers, and a file with
  mutual recursion and confirm the recursive pair share a layer.

## Likely files

- `static/app.js` — new layering function; no rendering change yet (that's
  ticket 015).

## Out of scope

Using the layers in the layout (ticket 015); methods inside classes,
class-vs-class layering; any backend/API change.
