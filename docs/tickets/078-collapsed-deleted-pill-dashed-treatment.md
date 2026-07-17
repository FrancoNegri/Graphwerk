# 078. Deleted status: distinct hue, and collapsed pills keep the dashed/faded look

Status: ready
Decision: docs/decisions/029-collapsed-deleted-pill-visual-treatment.md

*Hue superseded by [ADR 030](../decisions/030-status-palette-modified-green-deleted-red.md):*
`deleted` becomes red (`#ef4444`), not the stone grey below — the dashed/
faded collapsed-pill treatment this ticket describes is otherwise
unchanged. Acceptance criteria updated in place rather than forking a
duplicate ticket.

## Goal

`deleted` no longer reads as visually identical to `unchanged`, whether
collapsed or expanded: it gets its own hue instead of a shade of the same
slate, and a collapsed container whose `collapsedStatus` is `deleted` gets
the same dashed-border/reduced-opacity treatment an expanded `deleted`
node already has.

## Acceptance criteria

- `COLORS.deleted` in `static/app.js` is changed from a slate shade
  (`#64748b`) to `#ef4444` (red-500, per ADR 030 — the red `modified`
  vacates once ticket 079 recolors it).
- A collapsed container node (`node[collapsedStatus]`) with
  `collapsedStatus: 'deleted'` renders with a dashed border and reduced
  opacity, matching the existing `node[status='deleted']` treatment.
- A collapsed container node with any other `collapsedStatus` value is
  unaffected (no dashed border, full opacity as today).
- An expanded (non-collapsed) node's existing `status: 'deleted'`
  appearance keeps the dashed/reduced-opacity look, just with the new
  color.

## Likely files

- `static/app.js` — update `COLORS.deleted`; add/extend a Cytoscape style
  rule so the dashed-border + reduced-opacity treatment matches
  `collapsedStatus === 'deleted'` in addition to `status === 'deleted'`
  (the existing selector at the `node[status='deleted']` rule).
- `static/style.css` — the header legend's color dots and the sidebar's
  status chips read from a second, independent copy of the palette
  (`--deleted` custom property), not from `COLORS`. Missing this leaves
  the legend/chips showing the old slate while the graph shows the new
  red. Update `--deleted: #64748b` → `#ef4444` to match.

## Out of scope

- Any change to how `collapsedStatus` is computed/ranked (ADR 029 rejected
  folding the container's own status in).
- Palette changes to `modified`/`added`/`affected`.
- Symbol-move detection in the differ (separate future ticket, noted in
  ADR 029's out-of-scope).
