# 078. Collapsed deleted-status pills keep the dashed/faded look

Status: ready
Decision: docs/decisions/029-collapsed-deleted-pill-visual-treatment.md

## Goal

A collapsed file/class container whose `collapsedStatus` is `deleted` gets
the same dashed-border, reduced-opacity treatment an expanded `deleted`
node already has, so it no longer reads as visually identical to an
`unchanged` container.

## Acceptance criteria

- A collapsed container node (`node[collapsedStatus]`) with
  `collapsedStatus: 'deleted'` renders with a dashed border and reduced
  opacity, matching the existing `node[status='deleted']` treatment.
- A collapsed container node with any other `collapsedStatus` value is
  unaffected (no dashed border, full opacity as today).
- An expanded (non-collapsed) node's existing `status: 'deleted'`
  appearance is unchanged.

## Likely files

- `static/app.js` — add/extend a Cytoscape style rule so the dashed-border
  + reduced-opacity treatment matches `collapsedStatus === 'deleted'` in
  addition to `status === 'deleted'` (the existing selector at the
  `node[status='deleted']` rule).

## Out of scope

- Any change to how `collapsedStatus` is computed/ranked (ADR 029 rejected
  folding the container's own status in).
- Palette changes to `deleted`/`unchanged` colors.
- Symbol-move detection in the differ (separate future ticket, noted in
  ADR 029's out-of-scope).
