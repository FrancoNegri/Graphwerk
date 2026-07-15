# 051. Clicking a `calls` edge lists the calls it collapsed

Status: ready
Decision: docs/decisions/016-call-edge-status.md

## Goal

When several symbol-to-symbol `calls` edges collapse onto one rendered
edge (ticket 047's class collapse makes this common), clicking that edge
shows the reviewer exactly which underlying calls it represents instead of
silently hiding all but one.

## Acceptance criteria

- While building `edges` in `toElements`, instead of dropping every raw
  edge after the first with a given `(source, target, kind)` id
  (`seenEdgeIds`), collect the full list of raw `{source, target}` pairs
  that collapsed onto each representative edge and attach it as edge data
  (e.g. `data.calls`).
- A new `cy.on('tap', 'edge', ...)` handler, for edges of `kind ===
  "calls"`, renders that list in a small sidebar section (label pairs
  resolved via `nodesById`, e.g. `PaymentValidator.charge → Gateway.send`),
  showing one line when there's exactly one underlying call and a real
  list when there's more than one.
- Tapping empty canvas or a node clears/hides this section the same way
  `clearDetails` already does for the node details panel.
- Manual check: collapse two classes where one calls three different
  methods on the other, with "show calls" on — the single rendered edge
  between the two class chips, when clicked, lists all three method-level
  calls.

## Likely files

- `static/app.js` — `toElements` edge aggregation, new tap handler, a
  small sidebar section (and its markup) for the underlying-calls list.
- `static/index.html` — markup for the new sidebar section.

## Out of scope

- Edge status coloring (ticket 050, separate ticket).
- Any equivalent listing for `imports` edges.
