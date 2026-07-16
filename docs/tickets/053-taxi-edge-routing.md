# 053. Orthogonal (taxi) routing for calls/imports edges

Status: rejected — implemented and eyeballed against the agendabot dogfood
graph, then reverted. Even after tuning `taxi-direction: vertical` +
`taxi-turn-min-distance: 10px` to stagger overlapping bends, the user's
verdict on the live graph was to go back to bezier. `static/app.js` is back
to `curve-style: bezier`, no other change survived.
Decision: docs/decisions/018-orthogonal-edge-routing.md

## Goal

Calls/imports edges render with right-angle (Manhattan-style) routing
instead of bezier curves, so the graph reads closer to a schematic/PCB
trace layout — a cheap, reversible style experiment, not a layout change.

## Acceptance criteria

- The base `edge` selector's `curve-style` in the Cytoscape stylesheet
  (`static/app.js`, currently `bezier`) changes to `taxi`.
- `calls` and `imports` edges (kind-specific selectors immediately below
  the base one) keep their existing color/status styling — only the route
  shape changes, not which edges are colored how.
- No change to `graphwerk/layout.py` or any payload field — node
  `layer`/`order`/`group` positions are untouched; only how edges connect
  those positions visually changes.
- Manual check (per ADR 005 split — no JS test harness, eyeball in
  browser): serve the agendabot dogfood setup, toggle "show calls" and
  "show imports" on, confirm edges route in right angles rather than
  curves and remain click-able (`showEdgeCalls` still fires on tap).

## Likely files

- `static/app.js` — the Cytoscape stylesheet array (~line 277 `selector:
  "edge"`, `curve-style: "bezier"`).

## Out of scope

- Grid-snapping node x-coordinates for cleaner right angles (ADR 018 Out
  of scope — separate decision if taxi routing looks jagged as-is).
- Any change to `layout.py`, band/group computation, or the directory
  grouping tickets (035-037) — independent, sequenced separately per ADR
  018 Decision #3.
- Edge bundling or hub-node visual treatment (ADR 018 Decision #4).
