# 199. Doc-domain ADR layering

Status: done
Decision: docs/decisions/066-decision-graph-layering-and-ticket-visibility.md

## Goal

`GraphNode.layer` reflects real bottom-up lineage structure for the doc
domain instead of every ADR/ticket/root doc falling through to layer 0:
`docs/02-product-concept.md` is layer 0, ADRs with no incoming
`supersedes`/`amends`/`extends` edge ("founding" ADRs, ADR 065's existing
`grounds`-target definition) are layer 1, and an ADR that narrows a
layer-*N* ADR is layer *N+1*. Ticket nodes get no layer at all
(`None`), overriding today's default.

## Acceptance criteria

- `graphwerk/layout.py`'s `assign_layers` computes ADR layers by running
  `_layers_by_longest_path` (or an equivalent already-existing helper)
  over an adjacency built from `supersedes`/`amends`/`extends` edges
  (source ADR → target ADR), then shifts the result by +1 so a
  no-incoming-edge ("founding") ADR lands at layer 1.
- `docs/02-product-concept.md`'s node gets `layer = 0` explicitly.
- Ticket-domain file nodes (`docs/tickets/NNN-*.md`) get `layer = None`,
  overriding whatever the existing file-import adjacency would otherwise
  assign (today, an isolated layer 0).
- Using this repo's own real relationships (ticket 198's list — `015->002`,
  `030->029`, `042->037`, `050->037`, `058->037`, `058->050`
  (supersedes), `061->058` (amends), `025->009`, `041->005` (extends)) as
  a test fixture: 061 lands at layer 1, 058 at layer 2, 050 at layer 3,
  037 at layer 4 (the max of its three parents' layers + 1 — via 042: 2,
  via 058: 3, via 050: 4 — not the first-seen one), 002/029/009/005 at
  layer 2.
- An ADR with no relationship edges at all (the common case) lands at
  layer 1, same as one that's only ever a relationship *source*.
- Existing file-import and intra-file call-depth layering (code domain)
  is unaffected — same layers as before for every code-domain node.
- `_add_root_node`'s docstring comment claiming doc files "have no
  meaningful depth structure to anchor" (ADR 063) gets a one-line update
  noting this decision now anchors ADRs by `docs/02-product-concept.md`.

## Likely files

- `graphwerk/layout.py` — `assign_layers`, a new adjacency-building
  helper for `supersedes`/`amends`/`extends`, the +1 shift, the explicit
  product-concept/ticket overrides.
- `graphwerk/service.py` — `_add_root_node`'s stale comment (ADR 063).
- `tests/test_layout.py` (or wherever `assign_layers` is tested) — cases
  for founding-ADR layer 1, multi-parent max-layer resolution, product-
  concept at layer 0, tickets at `None`.

## Out of scope

- Any change to `_add_grounds_edges`, or reusing its output as the source
  of truth (this ticket recomputes "no incoming edge" independently via
  the longest-path helper's own root detection — same definition, no
  shared code needed, no edge-ordering dependency introduced).
- Frontend changes — the existing `layeredPlacementConstraints` in
  `static/app.js` already bands any file-kind node by `layer`,
  domain-agnostic; this ticket only needs correct `layer` values on the
  backend payload.
- Positioning revealed ticket nodes (ticket 200's concern).
