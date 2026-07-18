# 109. Session bar surfaces the check cycle

Status: done
Decision: docs/decisions/040-post-session-check-gate.md

## Goal

The reviewer can see where the cycle is — agent working, check running,
retrying, passed, or failed with the evidence — and gets the prompt bar
back exactly when graphwerk hands control over.

## Acceptance criteria

- The busy indicator names the phase from the `/api/session` payload:
  running (as today), `checking` ("validating…"), `resuming`
  (retry attempt shown).
- The prompt bar stays disabled through the entire cycle and re-enables
  only on a terminal state (`done` / `failed` / `check_failed`).
- `check_failed` shows a dismissible banner with the check's exit code
  and output tail (preformatted, scrollable); a cycle that ends `done`
  after a configured check shows a brief passed confirmation.
- With no check configured, the bar behaves exactly as today.
- Render-only JS: every string and state comes from the payload.

## Likely files

- `static/app.js` — session-poll handler renders the new states.
- `static/index.html` / `static/style.css` — banner element and styling.

## Out of scope

- Streaming check output (ADR 040: bounded tail after the fact only).
- Mapping failures to graph nodes (ADR 040 roadmap note).
- JS test harness (standing rule: user eyeballs the UI).
