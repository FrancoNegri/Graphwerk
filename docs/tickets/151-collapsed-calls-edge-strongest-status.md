# 151. Collapsed `calls` edges pick the most severe underlying status

Status: blocked: implemented in static/app.js, awaiting the user's manual browser verification against the dogfood tree (final acceptance criterion) — this skill doesn't check static/ changes itself
Decision: docs/decisions/055-collapsed-calls-edge-strongest-status.md

## Goal

A representative, collapsed `calls` edge shows the most severe status
among the raw calls it stands for, not whichever one happened to be seen
first while building the edge map.

## Acceptance criteria

- `toElements`'s edge dedup loop (`static/app.js`, ~lines 152-167) updates
  `edge.data.status` using `statusRank` as each raw call is folded in,
  identical to the comparison `strongestDescendantStatusByAncestor` already
  does for nodes.
- A collapsed edge representing one `unchanged` call and one `deleted` call
  (or any other severity mismatch) renders with the more severe status.
- `imports` edges unaffected — their status is always `UNCHANGED`, so no
  observable change is possible there.
- Manually verified in the browser against the dogfood tree: collapse a
  container pair with multiple underlying calls of differing status,
  confirm the line color matches the most severe one, and that clicking
  the edge still lists all underlying calls correctly. No automated test —
  this repo has no JS test harness (see ADR 055's "known gap" note); don't
  add one as a side effect of this ticket.

## Likely files

- `static/app.js` — `toElements`, the edge dedup loop.

## Out of scope

- Standing up a JS test runner / `package.json` — separate decision if
  ever wanted.
- Server-side move of this computation — rejected in the ADR (collapse
  state is client-only).
