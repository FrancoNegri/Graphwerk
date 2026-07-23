# 066. Decision-graph layering and ticket-node visibility

Status: proposed
Date: 2026-07-23
Extends: 046, 065

## Context

ADR 065 shipped a real lineage graph — `grounds`/`supersedes`/`amends`/
`extends`/`implements` edges are computed and rendered (tickets 191-198,
all done) — but two gaps are visible now that it's dogfooded against this
repo's own 65+ ADRs and 198+ tickets:

1. **No structural layout in Design mode.** `assign_layers()`
   (`graphwerk/layout.py`) only bands `imports` edges for code files and
   `calls` edges for functions; every doc-domain node — ADRs, tickets,
   `docs/02-product-concept.md` itself — falls through as an isolated node
   in that graph and lands at layer 0. The lineage edges ADR 065 added
   exist in the data and render as lines, but nothing arranges the nodes
   to make the lineage *readable* the way the code side's import-depth
   bands already do. The result the user is pushing back on: Design mode
   reads as a flat, undifferentiated scatter of ADR boxes — exactly the
   "structural context" failure mode docs/02 exists to fix, just
   relocated to the doc domain.
2. **Tickets leak into Implementation mode, and clutter Design mode.**
   ADR 065's `implements` edge (code file → ticket) was deliberately made
   to bypass the Design/Implementation domain filter in both directions
   ("stays visible regardless of the toggle"). In practice, with ~200
   tickets in this repo, that means every changed code file's ticket node
   shows up in Implementation mode, and every ADR's tickets show up
   unconditionally in Design mode — neither view stays legible at this
   corpus size.

This is a refinement of the just-shipped decision-lineage feature (ADR
065) and the mode toggle it renders into (ADR 046), not a new detour —
Phase 5's "knowledge base graph" is still the active thread; this is
finishing it to the point it's actually usable at this repo's own scale,
which is the dogfooding signal CLAUDE.md's workflow exists to catch.

## Decision

Two additive pieces, both reusing existing computed data — no new node
kind, no new edge kind, no new backend dependency:

**1. Bottom-up layering for the doc domain, computed in
`graphwerk/layout.py`, rendered by the frontend's existing file-band
machinery with zero new frontend layout code.**

`docs/02-product-concept.md` is layer 0 (it's a real, always-present node,
not a synthetic root — same call ADR 065 already made for the `grounds`
edge target, for the same reason: no synthetic stand-in needed for
something real that already exists). Every ADR's layer is computed by
running the *exact same* `_layers_by_longest_path` helper the file-import
band already uses, over a new adjacency built from `supersedes`/`amends`/
`extends` edges (source ADR → target ADR it narrows), then shifting the
result by +1:

- An ADR with no incoming `supersedes`/`amends`/`extends` edge is a "root"
  of that adjacency graph by the same definition `_layers_by_longest_path`
  already uses for import roots (no incoming edge from outside its SCC) —
  which is *exactly* ADR 065's own definition of a `grounds` target
  ("no incoming supersedes/amends/extends edge"). These land at base
  layer 0, shifted to **layer 1** — the "founding ADRs" layer. No new
  classification: this is ADR 065's already-shipped `grounds` computation,
  reused as the layering seed instead of recomputed.
- An ADR that supersedes/amends/extends a layer-*N* ADR lands at layer
  *N+1* — "the ADRs that affect [narrow/build on] each corresponding
  layer," same longest-path-from-root semantics the import band already
  uses, just walked in the direction these edges point (narrower →
  narrowed). Worked example from this repo's own real relationships
  (ticket 198's list): 061 (layer 1, nothing narrows it) *amends* 058 →
  058 is layer 2; 058 *supersedes* 050 → 050 is layer 3; 058 and 050 both
  *supersede* 037, and 042 (layer 1) also *supersedes* 037, so 037's layer
  is `max(via 042: 2, via 058: 3, via 050: 4) = 4` — the longest-path rule
  (already used for import depth) resolving the multi-parent case the same
  way it already does for diamond-shaped import graphs, including the
  longer 061→058→050→037 chain outranking the shorter 042→037 and 058→037
  ones.
- Ticket nodes get no layer (`None`) — explicitly excluded from the
  doc-domain layering pass, overriding whatever the existing file-import
  adjacency would otherwise assign them (today, an isolated layer 0). An
  unlayered node isn't banded by the frontend's existing
  `layeredPlacementConstraints`, so fcose places a revealed ticket by
  ordinary edge-length force toward its ADR instead of snapping into the
  layer spine — see Alternatives for why floating beats banding here.

Because ADR/root nodes are ordinary `kind="file"` nodes, the frontend's
existing `layeredPlacementConstraints` (`static/app.js`) already bands any
file-kind node by its `layer` field today, domain-agnostic — this decision
adds zero frontend layout code. It only works because Design and
Implementation mode already render mutually exclusive node sets (ADR 046's
domain filter), so a code file's layer and an ADR's layer never have to
coexist in the same band.

**2. Ticket-node visibility: hidden by default in both modes; revealed
only by clicking their linked ADR, and only in Design mode.**

Replaces the current unconditional `implements`-edge domain-filter bypass
(ticket 197) with a narrower, selection-driven rule in `static/app.js`:

- **Implementation mode never renders ticket nodes**, full stop — the
  code→ticket `implements` edge's ticket endpoint simply isn't in the
  rendered set there; the edge itself silently drops via the existing
  "both endpoints must render" rule (`toElements`'s
  `renderedIds.has(source) && renderedIds.has(target)` check), the same
  way any edge into a filtered-out node already does. No new drop logic
  needed.
- **Design mode renders a ticket node only when the currently-selected
  node is that ticket's ADR** (an `implements`-edge neighbor of
  `selectedId`). Computed as one more id-bypass Set, the same shape
  `crossDomainImplementsBypassIds` already is, just conditioned on
  selection instead of unconditional. Clearing the selection (tap empty
  canvas) or selecting an unrelated node hides revealed tickets again —
  reusing the selection-reset behavior `setIsolatedNode`/`clearDetails`
  already drive for ADR 056, not a new lifecycle.
- The existing `showImplementsView` toggle keeps its current job as a
  master kill-switch (off ⇒ no `implements` edges or ticket reveals at
  all, in either mode); this decision only narrows what happens when it's
  *on*.

## Alternatives considered

- **LLM/semantic layering** (infer an ADR's "generation" from prose) —
  rejected for the same reason ADR 065 already rejected semantic inference
  for relationship *kinds*: nondeterministic, re-answerable differently
  on every refresh, and this repo's ADRs already state the exact same
  information as an explicit, already-parsed edge. Free and deterministic
  beats inferred.
- **Band revealed tickets one layer below their ADR**, instead of leaving
  them unlayered/floating — would make a ticket's position predictable
  and consistent with the rest of the spine. Rejected for this pass: a
  ticket is a *transient* reveal (shown only while its ADR is selected),
  not a structural member of the lineage spine the way ADRs are; adding a
  real ticket layer would also force every revealed ticket into the same
  band regardless of how many tickets an ADR has, fighting fcose's own
  packing instead of leaving it free to lay siblings out sensibly. Revisit
  if a heavily-ticketed ADR's floating cluster reads as messier in
  practice than a fixed band would.
- **Keep the always-on `implements` bypass, but only shrink it to "current
  session's changed files' tickets"** (recency-based filtering instead of
  selection-based) — plausible for Implementation mode's original intent
  (surfacing "here's the ticket for what just changed"), but doesn't
  address Design mode's clutter at all, and reintroduces a second,
  independent notion of relevance (recency) alongside the click-based one
  this decision already needs for Design mode. Rejected in favor of one
  consistent rule (selection-driven reveal) rather than two different
  ones per mode.
- **A dedicated collapse/expand affordance for tickets** (double-click an
  ADR to pin its tickets open, mirroring file/class container collapse,
  ADR 010/056) instead of selection-driven, non-sticky reveal — persistent
  state the user has to remember to close again, and doesn't reuse any
  existing mechanism (container collapse operates on structural
  parent/child nesting; ADRs and tickets aren't nested, they're linked by
  edge). Rejected: selection-driven reveal reuses `selectedId`/
  `isolatedNodeId`, state the click handler already maintains for ADR 056,
  with no new persistent UI state to manage.

## Consequences

- No new `GraphNode`/`GraphEdge` fields or kinds — `layer` already exists
  on every node; this only changes *what value* doc-domain nodes get.
- `graphwerk/layout.py`'s `assign_layers` gains one more independently-
  layered adjacency (mirroring how it already runs the file-import graph
  and each file's call graph as separate passes) — same shape, new input
  edges.
- `_add_root_node`'s comment ("doc files have no meaningful depth
  structure to anchor," ADR 063) is now stale for ADRs specifically — this
  decision is that anchor, just pointed at the real `docs/02-product-
  concept.md` node instead of a synthetic one, exactly as ADR 065 already
  chose for the `grounds` edge. Ticket 063's comment gets a one-line
  update as part of implementing this.
- Zero new frontend layout code — the existing file-band constraint logic
  is reused as-is; this is the multi-language/multi-domain contract
  (`FileIndex`/`SymbolInfo` doesn't care what produced a node) paying off
  a second time.
- The `implements` edge keeps meaning what ADR 065 already defined; only
  its rendering default changes here — a display detail, which ADR 065
  itself flagged as this decision's territory ("a display detail, not an
  architectural one... the ticket implementing this decides").
- No invariant touched: Python computes layering, JS only maps numbers to
  fcose constraints (ADR 005); no hunk-to-symbol mapping; no new backend
  dependency.

## Out of scope

- Layering tickets themselves, or giving them any position rule beyond
  "float near your ADR when revealed" — see Alternatives.
- Any change to which three relationship kinds exist or how they're
  parsed — ADR 065 stands as decided; this only consumes the edges it
  already produces.
- Extending selection-driven reveal to any other node-pair relationship
  (e.g. revealing a code file's callers only on click) — scoped to the
  ticket-visibility clutter problem this decision names, not a general
  "everything starts collapsed" redesign.
- Reworking the `showImplementsView` checkbox's label/UI — it keeps doing
  exactly what it does today (global on/off), just gets a narrower "on"
  behavior.
- A synthetic root/anchor node for the doc domain (ADR 063's pattern) —
  `docs/02-product-concept.md` already is that anchor, real, no stand-in
  needed, same call ADR 065 already made for the `grounds` edge target.
