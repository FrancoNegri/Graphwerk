# 063. A synthetic `Root` node anchors the entry-point layer

Status: proposed
Date: 2026-07-22

## Context

ADR 022 flipped file layering so layer 0 means "entry point" — a file
nothing else imports sits at the top of the graph, regardless of how deep
its own dependency tree happens to descend. That fixed the *computation*,
but nothing on the rendered graph actually says so: a reviewer seeing a
cluster of file boxes at the top band has to already know the "layer 0 =
entry point" convention from the docs to read it that way. docs/02 frames
the whole point of the graph as giving "structural context" a flat diff
can't — "the graph shows... which callers are affected" — and the
top-of-graph band is exactly the piece of structure the layout already
computes but never labels.

## Decision

Add exactly one synthetic node, `Root`, to the code-domain file graph:

- Computed in `GraphService.snapshot()` as a post-processing step, after
  `assign_layers()` has run — not inside `graphwerk/layout.py` itself.
  `Root` isn't a layer computation (nothing new is being measured), it's a
  review-surface annotation over an already-computed result, the same
  category of work `_mark_affected`/`_add_import_edges` already are as
  snapshot-building steps in `service.py`.
- `id="__root__"`, `kind="root"`, `label="Root"`, `domain="code"`, no
  status/diff/why/code/source — it isn't a real file, so none of that
  applies. Fixed `layer=-1`, `order=0`.
- One new edge per code-domain file node currently at `layer == 0`:
  `GraphEdge(source="__root__", target=<file id>, kind="entrypoint")`.
- Scoped strictly to the *file* graph's top band — not to each file's own
  top-level-function call graph (ADR 003's per-file bands answer a
  different question, "what does this file call first," not "where does
  the app start"), and not to the doc domain: `references` edges
  (ADR 046) aren't consumed by `_import_adjacency` today, so nearly every
  doc file already sits at layer 0 with no meaningful depth structure —
  wiring `Root` to "all of them" wouldn't communicate anything, and "entry
  points to the app" (the user's own framing for this decision) is a
  code-specific concept to begin with.
- `layer=-1` needs no frontend change: `static/app.js`'s
  `appendBandConstraints` already sorts layers ascending
  (`layersTopFirst`, per ADR 022) and only requires at least two distinct
  layers to add a band constraint — `-1` simply sorts above `0` using the
  existing comparator.
- Rendering: a small, visually distinct node (e.g. a diamond, no fill
  tint, no status border since it has no status) with edges styled as
  thin/dashed rather than the solid `imports` treatment, so it reads as
  scaffolding rather than another changeable file. Always visible — not
  gated behind a per-kind toggle like `calls`/`imports`/`uses` (ADR 013),
  since it carries no change information to declutter and exists purely
  to anchor the top band. Selecting it can show a one-line description
  ("Entry points into this codebase") with no code/diff sections, since it
  has none.

## Alternatives considered

- **Style layer-0 file nodes directly (e.g. a badge/border), no synthetic
  node** — cheaper, no new node/edge kind. Rejected: doesn't scale to "one
  glance tells you this whole band is the entry surface" the way a single
  converging node does, and a per-node badge is easy to miss among the
  existing status-color border already used for change state; a shared
  `Root` above the band is a clearer, one-time visual anchor doing the
  same job the layering itself already does structurally (multiple roots
  converging on one concept).
- **Compute `Root` inside `graphwerk/layout.py`** — keeps all
  layer/order logic in one module. Rejected: `layout.py`'s own docstring
  and ADR 005 scope it to real graph-structure computation consumed
  generically by the frontend; `Root` is a UI-facing annotation with no
  structural meaning of its own (it doesn't get diffed, doesn't affect any
  other node's layer), so it belongs with the other snapshot-augmentation
  steps in `service.py`, not mixed into the layering algorithm itself.

## Consequences

- Purely additive: one node, one edge kind, computed from data
  `assign_layers()` already produces. No invariant touched — no new
  backend dependency, still Python-everywhere/JS-only-in-`static/`, no
  change to the differ or to `FileIndex`/`SymbolInfo`.
- `Root` never appears in `changed_paths()`/commit-all/revert-all (ADR
  061) or any diff-scoped computation — it's not a `FileChange` and never
  will be, since it's synthesized only in the snapshot step, after the
  diff has already been built.
- One more edge kind (`entrypoint`) and node kind (`root`) join
  `static/app.js`'s rendering surface, but with a narrower footprint than
  ADR 062's `uses`/`variable` — no per-kind visibility toggle, no code
  panel content beyond a static label.

## Out of scope

- Any equivalent anchor for the doc domain — no meaningful depth
  structure exists yet for docs (see Decision); revisit if/when doc-file
  layering is improved to consume `references` edges.
- A manually-configured entry point (e.g. a designated `main` module)
  distinct from the structural "nothing imports this file" definition —
  same posture ADR 022 already took: no evidence this repo needs a
  manual override.
- Any change to `_orders_by_barycenter`/directory grouping — `Root` is a
  single node with a fixed `order=0`; the existing multi-node ordering
  machinery isn't relevant to it.
