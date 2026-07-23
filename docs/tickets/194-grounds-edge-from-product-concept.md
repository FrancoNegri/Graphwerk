# 194. `grounds` edge: `docs/02-product-concept.md` → every foundational ADR

Status: ready
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

Every ADR that isn't itself a follow-on to another ADR (ticket 192's
edges) gets a visible `grounds` edge from the product concept doc — so
the graph has one literal, explorable root, the same way ADR 063 gave the
code domain one.

## Acceptance criteria

- After ADR relationship edges (ticket 192) are built, `GraphService.
  snapshot()` finds every `docs/decisions/NNN-*.md` node with no incoming
  `supersedes`/`amends`/`extends` edge, and adds `GraphEdge(source=
  "docs/02-product-concept.md", target=<that ADR's id>, kind="grounds")`.
- Computed as a post-processing step over already-built nodes/edges (same
  category of work as `Root`, ADR 063) — not folded into the doc-domain
  layering computation itself.
- `docs/02-product-concept.md`'s own node needs no special handling beyond
  already existing as an ordinary doc-domain file node (ADR 046) — this
  ticket only adds outgoing edges from it.
- A test with fixture ADRs — one with an incoming `amends` edge, one
  without — asserts only the un-amended one gets a `grounds` edge.

## Likely files

- `graphwerk/service.py` — new post-processing step in `snapshot()`,
  alongside the existing `Root`-node logic (ADR 063) it mirrors.
- `tests/` — snapshot-level test.

## Out of scope

- Any equivalent anchor from `docs/03-architecture-notes.md` or
  `docs/04-roadmap.md` — this decision names `docs/02-product-concept.md`
  specifically as the root (see ADR 065's Decision section); those two
  stay ordinary doc nodes, reachable only via existing generic
  `references` links when an ADR happens to link them.
- Any change to `Root`/`__root__` (ADR 063) itself — separate, code-domain
  only, untouched.
