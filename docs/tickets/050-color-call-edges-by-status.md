# 050. Color `calls` edges by their status

Status: done
Decision: docs/decisions/016-call-edge-status.md
Depends on: docs/tickets/049-call-edge-status-model.md

## Goal

A `calls` edge visually signals whether it leads into changed code, using
the same color vocabulary the reviewer already reads on nodes.

## Acceptance criteria

- `toElements` carries each edge's `status` field into the Cytoscape edge
  data (alongside `id`/`source`/`target`/`kind`).
- Cytoscape style maps a `calls` edge's line/arrow color from `status`
  using the existing `COLORS` table (same colors as node status), falling
  back to the current default gray for `status === "unchanged"`.
- `imports` edges are visually unaffected by this ticket.
- Manual check: in the demo graph, a `calls` edge pointing at a modified
  function renders red; one pointing at an added function renders blue;
  an edge that's the reason its source shows `affected` renders amber; an
  edge between two unrelated unchanged functions stays the current gray.

## Likely files

- `static/app.js` — `toElements` edge data, edge style selectors.

## Out of scope

- `imports` edge coloring (ADR 016, out of scope).
- The click-to-list-underlying-calls interaction (ticket 051).
