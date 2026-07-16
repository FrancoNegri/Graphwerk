# 022. Layer from entry points downward, not from leaves upward

Status: proposed
Date: 2026-07-16

## Context

ADR 002 introduced import-depth layering with the stated intent "entry
points at top, leaf utilities at bottom." The implementation computes each
node's layer as the **longest path to a sink** (a file importing nothing,
or a function calling nothing) — `_layers_by_longest_path` in
`graphwerk/layout.py`. A file that imports nothing sits at layer 0; a file
gets `layer = 1 + max(layer of everything it imports)`.

Dogfooding against agendabot (this session) surfaced the gap: three files
that are all genuine entry points — `webhook.py`, `trace/__main__.py`,
`validators/cross_file.py` — landed on layers 5, 4, and 2 respectively,
instead of together at the top. Each number is correct under the current
definition (it's how deep *that file's own* import chain happens to
descend before bottoming out), but it doesn't answer the question the
layout is supposed to answer for a reviewer: "is this near where the app
starts, or buried deep in its dependencies?" Two unrelated entry points
with differently-shaped dependency trees scatter across different bands
purely because of their own subtree depth, not because one is more
"entry" than the other. This undercuts the same "structural context"
promise (docs/02) ADR 002 was written to serve — the layer number stops
being a reliable read the moment a repo has more than one true entry
point, which real repos do.

This is the same kind of real-repo finding that already reshaped ADR 002's
own reasoning once directory grouping fell short (ADR 010) and once the
src-layout wrapper collapsed groups (ADR 021) — evidence from actually
using the tool on agendabot, not a hypothetical.

## Decision

Flip the direction `_layers_by_longest_path` propagates: compute each
node's layer as the **longest path from a root** (a file nothing imports,
or a function nothing calls), descending toward what it depends on,
instead of the longest path to a sink.

Concretely, in `graphwerk/layout.py`:
- A root (no incoming edges within that adjacency — file or function
  component) is layer 0.
- For every edge `source -> target` (source imports/calls target),
  `layer(target) = max(layer(target), layer(source) + 1)`.
- The existing SCC/cycle-collapsing machinery (Tarjan) is unchanged — only
  the direction of propagation flips. A cycle with no incoming edges from
  outside the cycle is itself a root at layer 0.
- This is one shared function used by both the file-import graph and each
  file's function-call graph, so the flip applies uniformly to both —
  consistent with the existing "deeper layer renders above what it depends
  on" convention already treating files-that-are-entry-points and
  functions-that-are-callers the same way.

`static/app.js`'s one comparator that decides which layer renders at the
top (`layersDeepestFirst` in `appendBandConstraints`) flips from
descending to ascending, so layer 0 — now "entry point" — anchors the top
band and increasing layer numbers step downward. No other rendering logic
changes: `_orders_by_barycenter`, `_grouped_by_directory`, and the
directory-grouping re-sort all operate purely on the numeric layer value
without caring what it means, so they need no change.

This satisfies the three properties driving the request:
- **Top nodes are entry points.** A root never has an incoming push (by
  definition nothing points at it), so it stays at its initialized 0 —
  and every unrelated entry point lands at the same layer 0, regardless of
  how deep its own dependency tree happens to go.
- **Each layer is one hop deep.** A node's layer is the length of the
  longest chain of edges reachable from any root that reaches it; every
  edge advances at least one layer relative to whichever root-ward path
  produced the source's own layer.
- **A node can only point at something with a strictly larger layer
  number.** For every edge `source -> target`, the update rule guarantees
  `layer(target) >= layer(source) + 1` unconditionally — there is no path
  through this algorithm that lets a node import/call something at its own
  layer or shallower.

## Alternatives considered

- **BFS / shortest path from any root** — simpler to describe, but a
  node's shortest distance from *some* root can be smaller than
  `layer(importer) + 1` if a different, shorter root chain also reaches
  it. That would let an edge point at a node with a layer number less than
  or equal to its own — exactly the invariant this decision is meant to
  guarantee. Longest-path-from-root is the only one of the two that holds
  the "can't point at something above you" rule unconditionally, for the
  same structural reason ADR 002 originally chose longest-path (over
  shortest-path) for the leaf-anchored version.
- **Keep sink-anchored layering, invert the displayed numbers** (e.g.
  `max_depth - own_depth`) — doesn't fix the actual complaint: it relabels
  each node's existing (still leaf-subtree-dependent) number, but three
  unrelated entry points with different subtree depths still end up at
  different distances from their own respective floors, so they still
  don't converge onto one top band. Rejected — cosmetic, not structural.
- **Root-based longest path (chosen)** — reuses the exact same SCC/cycle
  machinery already in place; the change is a reversed iteration order
  plus swapping which side of the update gets `max`'d. Smallest change
  that actually guarantees all three properties requested.

## Consequences

- Every existing layer-number assertion in `tests/test_layout.py` and
  `tests/test_service.py` flips to its mirrored value (e.g. a 3-hop import
  chain currently asserting the importer is layer 3 will instead assert
  the importer is layer 0 and the deepest sink is layer 3) — this is a
  full migration of the test suite's expected values, not a partial one,
  since one shared function backs every layer computed anywhere in the
  graph.
- `static/app.js`'s "deeper layer renders above" convention becomes
  "layer 0 renders above"; the one-line comparator flip plus its adjacent
  comment need updating together.
- Entry points across a real repo's file graph converge onto the same top
  band regardless of their own dependency-tree depth — the concrete
  problem this decision fixes.
- Touches no invariant: stays inside `graphwerk/layout.py` (stdlib-only)
  plus the one `static/app.js` consumer; no new backend dependency, no new
  cross-layer coupling, no change to the differ/models/apply contracts.

## Out of scope

- Anchoring layer 0 to an explicitly-designated entry point (e.g. a
  configured "main module") rather than the structural definition ("no
  incoming edges") — no evidence this repo needs a manual override; the
  structural definition already produces the grouping the dogfood run
  showed was missing.
- Any change to `_orders_by_barycenter` (left-right ordering) or
  `_grouped_by_directory` (ADR 010/021's directory grouping) — both
  already operate purely on numeric layer values and need no change under
  this flip.
- Spacing, banding visuals, or other layout tuning in `static/app.js`
  beyond the one comparator this decision requires.
