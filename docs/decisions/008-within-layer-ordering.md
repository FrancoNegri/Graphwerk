# 008. Within-layer ordering: barycenter sweeps to shorten cross-layer edges

Status: proposed
Date: 2026-07-15

## Context

ADRs 002/003 gave files and functions horizontal bands by import/call depth,
and ADR 005 moved that computation server-side. But *within* a band, order is
arbitrary: `app.js` chains same-band anchors left-to-right with
relative-placement constraints in node-list insertion order
(`appendBandConstraints`), which also *pins* that order — fcose's forces
cannot reorder a band even when an edge is stretched across it. So a file in
layer 3 and its importer in layer 2 can land at opposite horizontal ends,
producing long diagonal edges and crossings. The graph reads messy, which
undercuts the product concept's core bet (docs/02): the graph is only a
better review surface than a diff if you can follow its structure at a
glance. This continues Phase 2's Scale UX line (docs/04), one step after
ADRs 002/003/005.

## Decision

Add the classic within-layer ordering step of the Sugiyama framework — the
**barycenter heuristic** — to `graphwerk/layout.py`, and expose the result
as a new `GraphNode.order` payload field that `app.js` uses to sort each
band's left-to-right chain:

- For each layered graph we already build (files via `imports` edges;
  each expanded file's top-level functions via intra-file `calls` edges),
  start from a deterministic initial order (node id) and run a fixed small
  number of alternating downward/upward sweeps. Each sweep re-sorts every
  layer by the mean position (barycenter) of each node's neighbors in the
  adjacent layer; nodes with no neighbors there, and ties, keep their
  previous relative order (stable sort), so the result is deterministic.
- Edges spanning more than one layer use the neighbor's actual order
  directly — no dummy/virtual nodes.
- `GraphNode.order` is an integer for every node that has a `layer`, `null`
  otherwise — exactly mirroring the `layer` field's contract from ADR 005.
- `app.js` sorts each band's anchors by `order` before chaining them; no
  other presentation change. Python logic gets pytest coverage; the browser
  outcome is verified visually by the user (ADR 005 testing split).

## Alternatives considered

- **Drop the left-right chain and let fcose forces order each band** —
  zero new code, but forfeits the minimum-gap guarantee the chain exists
  for (bands crowd again), and the resulting order is nondeterministic and
  still fights the alignment constraint. Rejected.
- **Swap to a purpose-built hierarchical engine (dagre/elk)** — already
  rejected in ADR 002: poor compound support (dagre), heavy new vendored
  dependency (elk), discards working fcose tuning.
- **Exact crossing minimization (ILP or full Sugiyama with dummy nodes)** —
  the problem is NP-hard; barycenter is the standard heuristic and the
  graphs here (files per repo, functions per file) are small. Extra
  precision isn't worth the code. Rejected; dummy-node refinement can be a
  later increment if long edges still read badly.

## Consequences

- Connected nodes in adjacent bands pull horizontally close; edge crossings
  drop; the layered reading finally works left-to-right as well as
  top-to-bottom.
- `order` joins `layer` in the `/api/graph` contract; new language
  extractors inherit it for free, same as layers (ADR 005).
- Band order becomes deterministic across refreshes — a stability win over
  today's insertion-order accident.
- The ordering optimizes each granularity independently (files globally,
  functions per file), consistent with ADR 003's file-local framing.
- Touches no invariant: Python-side, stdlib-only, additive payload field,
  presentation JS stays a consumer.

## Out of scope

- Dummy/virtual nodes for edges spanning multiple layers (later increment
  if needed).
- Edge routing/bundling, curved edges.
- Ordering classes or methods-in-classes (unlayered today — follows ADR
  003's deferral).
- X-coordinate assignment: fcose still positions nodes; we only fix their
  relative order and keep the existing 190px minimum gap.
- Persisting layout across reloads (out of scope since ADR 002).
