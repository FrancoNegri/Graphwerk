# 031. Bands chain anchors in payload order

Status: done (pending the user's visual check on the demo graph)
Decision: docs/decisions/008-within-layer-ordering.md

## Goal

`static/app.js` sorts each band's anchors by the backend's `order` field
before chaining them left-to-right, so the pinned within-band sequence is
the barycenter-optimized one instead of insertion-order accident.

## Acceptance criteria

- Anchors within each layer (both file bands and per-file function bands)
  are sorted by their node's `order` before the left-right
  relative-placement chain is built; nodes with `null` order sort last,
  stably.
- No other layout behavior changes: band membership, vertical gaps, and
  the 190px minimum horizontal gap stay as they are.
- `app.js` only reads the `order` field — no graph traversal or
  re-derivation in JS (ADR 005).
- Verified visually by the user on the demo graph: cross-layer edges
  between connected files are visibly shorter/less crossed than before.

## Likely files

- `static/app.js` — sort in `layeredPlacementConstraints` /
  `appendBandConstraints`

## Out of scope

Any Python change (tickets 029/030); edge routing or styling tweaks.
