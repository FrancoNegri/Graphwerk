# 058. Tune wheel-zoom sensitivity and bounds

Status: done
Decision: docs/decisions/020-edge-hover-reveal-and-zoom-feel.md

## Goal
Mouse-wheel zoom on the graph feels controllable at both ends instead of
overshooting into an unreadable zoomed-out speck or an unusably close
zoomed-in view.

## Acceptance criteria
- `wheelSensitivity` in the `cytoscape(...)` config (`static/app.js`,
  currently `0.3` at line 236) is retuned by feel during implementation.
  (Corrected 2026-07-17, audit F-004: the original "lower toward
  `0.15`–`0.2`" guess was wrong — tuning went *up*, shipping as `5`, with
  the `minZoom`/`maxZoom` bounds below taking over the overshoot
  protection. User-confirmed intended; see the ADR 020 amendment.)
- `minZoom` and `maxZoom` are set on the same config so scrolling can't
  push the graph past a legible range in either direction.
- Manually verified in the browser (per CLAUDE.md: curl/API checks don't
  cover this — this is a feel change, eyeball it): zoom in/out over the
  demo graph and confirm neither extreme is reachable and the per-notch
  step feels smooth.

## Likely files
- `static/app.js` — `cytoscape(...)` config object, ~line 233-236.

## Out of scope
- Touch/pinch-zoom tuning (desktop/mouse-first UI today).
- Any change to layout (`fcose`) options — zoom is a viewport property,
  unrelated to node placement.
