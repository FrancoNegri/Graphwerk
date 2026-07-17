# 094. Prompt bar docks to the bottom of the viewport

Status: ready
Decision: docs/decisions/037-bottom-session-bar-commit-discard.md

## Goal

The prompt bar renders as a bar fixed to the bottom of the screen instead
of sitting under the header, making room for it to grow into the session
bar (tickets 095–099).

## Acceptance criteria

- `#prompt-bar` is docked at the bottom edge of the viewport, full width,
  above the toast layer; the graph canvas and sidebar are not overlapped
  (the `main` area accounts for the bar's height).
- Prompt input, Run button, busy spinner, and error span all keep working
  unchanged — this is a placement-only change.
- Verified by eyeballing the served UI at desktop widths per the
  project's JS/CSS practice.

## Likely files

- `static/index.html` — move the `#prompt-bar` block below `main`
- `static/style.css` — docked-bar layout, `main` height adjustment

## Out of scope

The commit message box and buttons (tickets 095–099). Any behavior change
in prompt submission or polling.
