# 048. `show-calls` defaults to on

Status: done
Decision: docs/decisions/015-contract-by-default.md

## Goal

The graph shows `calls` edges on first load without the reviewer having to
check a box; `imports` stays unchecked, unchanged from ticket 046.

## Acceptance criteria

- `static/index.html`'s `show-calls` checkbox renders pre-checked.
- `static/app.js`'s `showCallsView` initializes to `true` (rather than
  `false`); `showImportsView` stays `false`.
- Manual check: load the demo graph fresh (no prior interaction) — solid
  `calls` edges are visible immediately; dashed `imports` edges are not,
  until "show imports" is checked.

## Likely files

- `static/index.html` — add `checked` to the `show-calls` input.
- `static/app.js` — flip `showCallsView`'s initial value.

## Out of scope

- Any change to `showImportsView`'s default (stays off).
- Edge status coloring (tickets 049-050).
