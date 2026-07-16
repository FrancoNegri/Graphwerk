# 075. UI marker for describes-only rationale

Status: ready
Decision: docs/decisions/027-rationale-must-justify-not-describe.md

## Goal

When a node's `why_justifies` (ticket 074) is `false`, show a subdued
marker next to `why` distinct from the existing low-confidence marker
(ticket 069) — this text is attributed correctly, it just may not explain
*why* the change serves the request.

## Acceptance criteria

- Sidebar `why` section reads `why_justifies` and, when `false`, renders a
  small inline label (e.g. "may only describe the code, not justify the
  change") separate from and compatible with the existing
  `why_confident`-based label — a node could show one, both, or neither.
- No label when `why_justifies` is `true` or `None`.
- No new JS logic beyond reading the field and toggling the label, per the
  thin-JS rule (ADR 005).

## Likely files

- `static/app.js` — extend the why-section rendering alongside the
  existing `why_confident` marker (ticket 069).
- `static/style.css` (or wherever the sidebar is styled).

## Out of scope

- How `why_justifies` is computed (ticket 074).
