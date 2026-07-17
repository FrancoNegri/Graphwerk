# 079. `modified` status turns green

Status: done
Decision: docs/decisions/030-status-palette-modified-green-deleted-red.md

*[ADR 031](../decisions/031-modified-status-blue-not-green.md) briefly
proposed cyan instead; rejected same day after seeing it rendered, before
this ticket shipped. Back to green, as below.*

## Goal

`COLORS.modified` (and the matching CSS custom property) changes from red
to green, everywhere it's used: node fills/borders, `calls` edges, the
header legend, and the sidebar status chip.

## Acceptance criteria

- `COLORS.modified` in `static/app.js` is `#22c55e` (green-500), not
  `#ef4444`.
- `--modified` in `static/style.css` is `#22c55e`, matching.
- The header legend dot for "modified" and the sidebar's `.chip.modified`
  render the new green (both read from `--modified`, so this should fall
  out of the variable change — verify, don't assume).
- A `calls` edge with `status: 'modified'` renders green (falls out of
  `COLORS[status]` lookup in the edge style — verify, don't assume).
- `affected`, `added`, `deleted`, `unchanged` are untouched by this ticket.

## Likely files

- `static/app.js` — `COLORS.modified`.
- `static/style.css` — `--modified` custom property.

## Out of scope

- `deleted` → red (ticket 078, amended for ADR 030).
- The `#prompt-error` coupling to `var(--modified)` (ticket 080) — do not
  fix incidentally here; keep this ticket to the color value itself so the
  before/after is a clean single-variable diff. If `#prompt-error` visibly
  turns green while testing this ticket, that's ticket 080's problem to
  fix, not a sign this ticket is incomplete.
