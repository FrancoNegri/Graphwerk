# 200. Ticket-node selection-driven visibility

Status: done
Decision: docs/decisions/066-decision-graph-layering-and-ticket-visibility.md

## Goal

Ticket nodes never clutter Implementation mode, and in Design mode only
appear while their linked ADR is selected — replacing the current
unconditional cross-domain bypass for the `implements` edge.

## Acceptance criteria

- In Implementation mode, no ticket node ever renders, regardless of
  `showImplementsView` — a code file's `implements` edge to its ticket
  silently drops (both-endpoints-must-render rule already in
  `toElements`), same as any edge into a filtered-out node.
- In Design mode, a ticket node renders if and only if `showImplementsView`
  is on **and** it's an `implements`-edge neighbor of the currently
  selected node (`selectedId`)/isolated node. Selecting a different node,
  or tapping empty canvas to clear selection, hides it again.
- `crossDomainImplementsBypassIds` (or its replacement) no longer makes
  ticket visibility unconditional; the selection-driven Set is computed
  alongside the existing domain-filter/isolation logic in `toElements`,
  reusing `selectedId`/`isolatedNodeId` rather than introducing new
  selection-tracking state.
- Turning `showImplementsView` off hides ticket reveals entirely in Design
  mode too (it stays the master kill-switch ADR 065/197 already gave it).
- Manually verified against this repo's own docs (dogfooding, per
  CLAUDE.md): in Implementation mode, no ticket boxes appear anywhere on
  the canvas; in Design mode, selecting an ADR with landed tickets shows
  exactly those tickets, and tapping empty canvas or a different node
  hides them again.

## Likely files

- `static/app.js` — `toElements`'s node filter, the
  `crossDomainImplementsBypassIds` replacement, `setIsolatedNode`/tap
  handlers (re-render on selection change already happens via
  `showDetails`/`setIsolatedNode`'s existing call path).

## Out of scope

- Any layout/positioning change for revealed ticket nodes — they render
  unlayered/free-floating per ADR 066 (ticket 199 covers giving them
  `layer = None` on the backend).
- Extending selection-driven reveal to any other edge kind or node pair.
- Changing the `showImplementsView` checkbox's label or the sidebar
  relationship-list rendering (ADR 065/ticket 197) — unaffected here.
