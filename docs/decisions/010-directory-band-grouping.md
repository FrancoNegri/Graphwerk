# 010. Directory-aware band grouping: files cluster by top-level directory within layers

Status: proposed
Date: 2026-07-15

## Context

ADR 002 gave files import-depth bands and explicitly deferred
"directory-based grouping" with the condition *revisit if import depth
proves a poor proxy for architecture*. The agendabot dogfood run (July
2026, 99 files / 1426 nodes) is that evidence: every band mixes `src` and
`tests` files (the widest band is 10 src + 22 tests chained in one 32-chip
row), so while the *vertical* axis answers "how deep in the import graph",
nothing answers "what part of the codebase is this" — the reviewer reads
labels chip by chip. The product concept's structural-context promise
(docs/02) and Phase 2's Scale UX line (docs/04) both presume the graph is
scannable; this continues ADRs 002/005/008 one increment further.

## Decision

Group each band's files by top-level directory, server-side, and give the
UI a field to make the grouping visible:

1. **Grouped within-band ordering.** After the barycenter sweeps (ADR 008),
   re-sort each file band so files sharing a top-level directory (`src`,
   `tests`, repo root, …) are contiguous. Group order within the band is
   the mean barycenter position of its members (so the edge-shortening the
   sweeps bought is preserved between groups); members keep their
   barycenter order inside the group. Deterministic, stdlib-only, in
   `graphwerk/layout.py`, covered by pytest.
2. **`GraphNode.group` payload field.** File nodes carry the grouping key
   (top-level directory; `null` for non-file nodes). Computing it
   server-side keeps the ordering and the visual cue from ever drifting
   apart, mirroring how `layer`/`order` ship precomputed (ADR 005).
3. **Visual cue in the UI.** `app.js` maps each distinct `group` to a
   subtle background tint from a fixed palette (status colors stay on the
   border, untouched) plus a small legend. Presentation-only JS, verified
   by eyeballing per ADR 005's testing split.

Symbol bands (functions inside a file, ADR 003) are unaffected — grouping
only applies to the file-level graph, where directories exist.

## Alternatives considered

- **Compound directory parent nodes (dir ⊃ file ⊃ class ⊃ function)** —
  the strongest visual grouping, but adds a third nesting level to the
  compound/collapse/band-constraint machinery that took ADRs 002/003/008
  to stabilize; high interaction risk with fcose for a first increment.
  Deferred — worth revisiting if tint + contiguity prove too weak.
- **Two-dimensional lanes: column per top-level directory × band per
  depth** — answers "what goes where" most literally, but over-constrains
  fcose (every node pinned in both axes) and is a layout redesign, not the
  "improved a little" this needs. Rejected for now; noted as the natural
  follow-up if grouping succeeds.
- **Pure barycenter order with a tint but no regrouping** — cheapest, but
  agendabot's bands interleave src/tests heavily, so tints alone would
  produce a striped row, arguably noisier than today. Rejected;
  contiguity is what makes the tint readable.

## Consequences

- Bands read as labeled runs — "these five chips are `tests`, those are
  `src`" — so a changed node's position answers both *how deep* (band) and
  *where in the tree* (group) at a glance.
- Grouping trades away some barycenter optimality inside a band (edges
  between groups may stretch slightly); accepted — ADR 008's sweeps still
  set group order, and legibility is the current bottleneck.
- `group` joins `layer`/`order` in the `/api/graph` contract — additive;
  new language extractors inherit it for free since it derives from `path`.
- Touches no invariant: Python-side, stdlib-only, JS stays a consumer.

## Out of scope

- Compound directory nodes and 2D directory lanes (see alternatives —
  revisit after this increment is judged in the same dogfood setup).
- Grouping below the top level (`src/agendabot/handlers` vs
  `src/agendabot/db`) — only if top-level proves too coarse on real repos.
- Band wrapping for very wide bands (multiple rows per layer) — separate
  legibility lever, its own decision if width remains painful.
- Excluding or de-emphasizing test files from layering — the changed-only
  toggle (ticket 006) already covers focus; hiding structure is a
  different product call.
