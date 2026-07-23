# 197. Frontend: render `supersedes`/`amends`/`extends`/`grounds`/`implements` edges

Status: ready
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

A reviewer can actually see the new lineage edges on the graph — distinct
enough from `calls`/`imports`/`uses`/`references` to read at a glance as
"this is decision lineage, not code structure."

## Acceptance criteria

- `static/app.js` renders `supersedes`, `amends`, `extends`, `grounds`, and
  `implements` edges with their own visual treatment (distinct from the
  existing code-domain edge styles and from generic `references`) — exact
  colors/line styles are this ticket's call, but each of the five must be
  visually distinguishable from the others when both ends are visible.
- These edge kinds join the existing per-kind visibility toggle family
  (ADR 013) rather than always-on — **except** `implements` at the code→
  ticket hop specifically, which per ADR 065's Decision section renders
  regardless of the Design/Implementation domain toggle (ADR 046), since
  it's the one edge kind meant to cross that boundary. `supersedes`/
  `amends`/`extends`/`grounds` stay doc-domain-only and are hidden
  entirely when the Implementation view is active, same as any other
  doc-domain element.
- Selecting an ADR node's sidebar shows its typed relationships as a short
  labeled list (reusing the existing "Affects"-line rendering pattern,
  ADR 062/ticket 184, for visual consistency) rather than requiring the
  reviewer to trace edges on the canvas by eye alone.
- Manually verified against this repo's own docs (dogfooding, per
  CLAUDE.md): select `docs/02-product-concept.md` and confirm foundational
  ADRs show as `grounds` targets; select ADR 058 and confirm `supersedes`
  edges to 037/050 and an incoming `amends` edge from 061 (once ticket 193
  lands); select a landed ticket and confirm `implements` edges to the
  files its commit actually touched.

## Likely files

- `static/app.js` — edge styling, sidebar relationship list.
- `static/style.css` (or wherever edge/legend styles live) — new edge
  color/line treatments, legend entries.

## Out of scope

- Any change to the existing `calls`/`imports`/`uses`/`references`
  toggles or their current visual treatments.
- A dedicated "lineage view" separate from the existing graph canvas —
  this is the same graph, same canvas, new edge kinds on it.
