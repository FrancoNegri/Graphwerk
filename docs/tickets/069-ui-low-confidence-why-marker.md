# 069. UI marker for low-confidence rationale

Status: ready
Decision: docs/decisions/025-rationale-mention-confidence.md

## Goal

When a node's `why` came from the proximity fallback rather than a
guidance bullet or explicit prose mention (ticket 068's `why_confident`
field), show a subdued marker next to it in the sidebar so the reviewer
doesn't read it with the same trust as a direct explanation.

## Acceptance criteria

- Sidebar `why` section reads the new payload field and, when
  `why_confident` is `false`, renders a small inline label (e.g.
  "unconfirmed — nearest narration, not a direct mention") next to the why
  text.
- No label shown when `why_confident` is `true` or absent (sidecar-sourced
  rationale, unaffected nodes).
- No new JS logic beyond reading the field and toggling the label, per the
  thin-JS rule (ADR 005) — styling only, no re-derivation of confidence in
  the browser.

## Likely files

- `static/app.js` — extend the existing why-section rendering
  (`whySection`/`d-why`, around the code that shows/hides based on
  `node.why`).
- `static/style.css` (or wherever the sidebar is styled) — subdued label
  styling.

## Out of scope

- Any change to how confidence is computed (ticket 068).
- The existing rationale-source banner (ticket 034) — this is a per-node
  marker, separate from that per-session banner.
