# 037. Directory tint + legend in the UI

Status: ready
Decision: docs/decisions/010-directory-band-grouping.md

## Goal

The grouping from tickets 035/036 is visible: chips sharing a top-level
directory share a subtle background tint, with a small legend mapping
tint → directory.

## Acceptance criteria

- `app.js` assigns each distinct `group` value a background tint from a
  fixed palette (stable assignment order, e.g. first-seen in payload
  order); file nodes get the tint on both collapsed chips and expanded
  boxes. Status colors stay on borders exactly as today.
- A legend element lists group → tint; hidden when every file shares one
  group (single-package repos and the demo stay visually unchanged apart
  from that single tint or none).
- JS consumes the `group` field only — no path parsing client-side.
- Verified by eyeballing demo and the agendabot setup (project testing
  convention; no JS test harness).

## Likely files

- `static/app.js` — tint mapping + legend
- `static/style.css`, `static/index.html` — legend styling/placement

## Out of scope

- Compound directory parent nodes; 2D directory lanes (ADR 010
  alternatives — later increments).
- User-configurable palettes.
