# 002. Graph layout legibility: collapse-by-default + import-depth layers

Status: proposed
Date: 2026-07-14

## Context

Running against a real repo (agendabot) the graph opens messy: file nodes
are Cytoscape compound boxes that size to their symbol count, so a
30-symbol module dwarfs a one-symbol file, and fcose lets the boxes overlap.
The reviewer has to hunt. The product concept (docs/02) only holds if the
graph is a *more* comfortable review surface than a flat diff — "structural
context" and "blast radius for humans" both presume you can read the thing.
This is a continuation of Phase 2's "Scale UX" line (docs/04), following
collapse/expand (ticket 005) and the changed-only toggle (ticket 006).

## Decision

Two moves, shipped incrementally:

1. **Collapse by default.** Unchanged files start collapsed to a chip of
   uniform size; changed and blast-radius files start expanded. The
   existing double-click toggle overrides the default per file, and the
   user's manual choice wins over the policy across refreshes. This
   harmonizes node sizes (the bulk of the graph becomes same-sized chips)
   and removes most overlap pressure, while the files that matter for
   review stay open.

2. **Layers by import depth.** Compute a layer per file from the
   file-level import edges (longest-path depth; cycles fall into the same
   layer) and place files in horizontal bands — entry points at top, leaf
   utilities at bottom — via fcose's alignment/relative-placement
   constraints. A changed node's vertical position then tells the reviewer
   *where in the architecture* the change lands, which is exactly the
   structural-context promise.

All of it is presentation logic in `static/app.js`. No backend change, no
new vendored library (cytoscape-fcose, already vendored, supports the
constraints).

## Alternatives considered

- **Tune fcose knobs only** (repulsion, separation, tiling) — cheapest, but
  fixes neither the size disparity (driven by compound sizing, not the
  layout) nor the lack of structure; rejected as insufficient alone, though
  separation tuning rides along with the chosen option.
- **Swap layout engine to dagre/elk** — purpose-built hierarchical layouts,
  but dagre's compound-node support is poor, elk is a heavy new vendored
  dependency, and both discard the working fcose tuning and
  position-carrying logic; rejected.
- **Collapse-by-default only, no layers** — valuable and cheaper, but the
  user explicitly wants a layered reading and organic placement wastes the
  import graph we already have; kept as the first increment rather than
  the whole decision.

## Consequences

- Big repos open readable: uniform chips, expanded only where review
  attention goes, architecture visible as vertical bands.
- The collapse *default* becomes state derived from node status, layered
  under the existing manual toggle — the interaction model gains a
  policy-vs-override distinction that must survive graph refreshes.
- Import cycles (common in real repos) must degrade gracefully — same
  band, never a crash or infinite loop.
- Touches no invariant: differ, models, backend deps, and the
  Python-everywhere rule are all untouched.

## Out of scope

- Directory-based grouping or manual layer pinning (revisit if import
  depth proves a poor proxy for architecture).
- Persisting layout/collapse state across page reloads.
- Symbol-level layout inside a file box; dagre/elk migration.
- Rationale-quality work spotted in the same dogfood run (roadmap Phase 5
  note; separate north-star pass).
