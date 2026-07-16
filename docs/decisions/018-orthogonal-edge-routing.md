# 018. Orthogonal (taxi) edge routing; defer bespoke hub treatment until it's judged with directory grouping

Status: rejected (tried on ticket 053, reverted)
Date: 2026-07-15

## Context

Dogfooding against agendabot this session (`/api/graph`, base agendabot /
staged agendabot-graphwerk-staging) surfaced a legibility question ADRs
002/005/008/010 hadn't addressed yet: **edge rendering style**, not just
node placement. Numbers from the live run:

- Raw flat graph: 1455 nodes / 8793 edges — but 44% of `calls` edges
  (3800/8570) touch just 20 hub nodes, almost all a single pattern
  (`TestX._call`, a shared mock-dispatch helper called from every test
  method in a class). Container-collapse (tickets 010/047) already absorbs
  most of this — it's not the real rendering problem.
- What's actually rendered by default (everything collapsed): 104 file
  nodes, 390 cross-file `calls` edges, avg degree 7.5, max 35
  (`src/agendabot/models/templates.py`).
- The vendored `static/vendor/cytoscape.min.js` already ships `taxi`
  (orthogonal/Manhattan) edge routing — confirmed present, unused today
  (current stylesheet sets `curve-style: bezier` on the base `edge`
  selector, `static/app.js` ~line 280).

The user asked specifically whether a PCB/schematic-style diagram (clean
right-angle traces, minimal crossings) is achievable. This continues Phase
2's Scale UX line (docs/04) and is a direct extension of ADR 008 (which
explicitly deferred "edge routing/bundling, curved edges") and ADR 010
(directory grouping — tickets 035-037 already scoped, not yet
implemented), not a new area.

## Decision

1. **Switch `calls`/`imports` edges to `taxi` (orthogonal) routing** —
   a Cytoscape stylesheet change in `static/app.js`, presentation-only,
   verified by eyeballing the running UI per the established testing split
   (ADR 005: JS is a consumer, no JS test harness). This is the cheap,
   reversible experiment: it costs a few lines and directly answers "does
   right-angle routing read better than bezier curves" without touching
   layout logic.
2. **Do not grid-snap node x-coordinates in this decision.** ADR 008
   explicitly left x-coordinate assignment to fcose (only relative order +
   minimum gap are fixed). Taxi routing on continuous, non-grid-aligned
   positions may look stair-stepped rather than clean — that's an expected,
   visible tradeoff of trying the cheap option first, not a defect to
   silently work around. Judge it as rendered; a grid-snapping layout
   change is a separate, bigger decision (see Out of scope).
3. **Sequence this behind — or alongside — the already-scoped directory
   grouping tickets (035-037, ADR 010).** Those tickets are `ready` but
   unimplemented, and this session's numbers show they'd directly shrink
   the dominant hub's effective degree at the tier reviewers actually see
   by default (17 top-level directories vs. 104 files) before this
   decision's routing style is judged. Evaluating taxi routing on today's
   ungrouped bands would confound "is orthogonal routing good" with "is the
   band still too wide" — implement 035-037 first, or at least before
   judging this ticket's outcome.
4. **No bespoke hub fan-out treatment (edge bundling, degree-based
   dimming/thresholds) in this decision.** The two levers above (routing
   style + directory grouping) are both cheap, already-reasoned-about, and
   untried in combination — building a third, overlapping mitigation before
   seeing how far those two get is speculative. Revisit only if hub nodes
   still dominate the picture after both land.

## Alternatives considered

- **Vendor a purpose-built layered/orthogonal engine (ELK, dagre) for a
  true crossing-minimizing PCB autorouter** — closest to the user's mental
  model of a real PCB, but ELK/dagre were already rejected twice (ADR 002:
  poor compound support in dagre, heavy new dependency in ELK; ADR 008:
  same). A third rejection for the same reasons; nothing about this
  decision changes that calculus. Rejected.
- **Build hub-node treatment now** (bundle or dim edges above a degree
  threshold) — attacks the sharpest pain point directly, but ADR 010's
  tickets 035-037 already target exactly this class of problem and haven't
  shipped yet; adding a second, untested mitigation before judging the
  first is duplicate speculative work. Rejected for now — revisit after
  035-037 + taxi routing are both dogfooded.
- **Do nothing (keep bezier curves)** — zero cost, but leaves a two-line,
  fully reversible experiment untried when the user explicitly asked the
  question. Rejected.

## Consequences

- Calls/imports edges gain a more schematic, right-angle look; whether it
  actually reads as "PCB-like" depends on how much the continuous fcose
  x-coordinates undercut it — an open question this decision deliberately
  leaves for eyeball judgment rather than pre-solving with a bigger layout
  change.
- Directory grouping (035-037) gets an added reason to land soon: it's now
  both ADR 010's own legibility fix and a prerequisite for fairly judging
  this decision.
- Touches no invariant: JS-only, presentation-only, no backend or payload
  change, no new dependency.

## Outcome

Tried on ticket 053 against the live agendabot dogfood graph (today's
ungrouped, 104-file band). The predicted risk in Consequences above
materialized: continuous, non-grid fcose x-coordinates made right-angle
edges overlap heavily on shared vertical/horizontal tracks. Tuning
Cytoscape's `taxi-direction: vertical` + `taxi-turn-min-distance: 10px` (to
stagger bend points) visibly reduced the overlap but didn't clear the bar —
the user's eyeball verdict on the tuned version was still to revert.
`static/app.js` is back to `curve-style: bezier`; see ticket 053.

This was judged before directory grouping (035-037) landed, i.e. exactly
the confounded ordering Decision #3 flagged as a risk — a re-trial after
035-037 ships, on a lower-degree graph, is still open and not ruled out by
this result.

## Out of scope

- Grid/column-snapped x-coordinates for a true clean-trace look — real
  layout change, only worth it if taxi routing on today's continuous
  positions looks jagged rather than clean once tried.
- Edge bundling or degree-based visual treatment for hub nodes — deferred
  per Decision #4, revisit with post-grouping numbers.
- 2D directory lanes / compound directory nodes — already out of scope per
  ADR 010, unchanged here.
- Orthogonal routing for any edge kind other than `calls`/`imports` — none
  currently exist.
