# 055. Collapsed `calls`-edge status picks the most severe underlying call, not the first

Status: proposed
Date: 2026-07-20

## Context

Found alongside [054](054-deleted-caller-edge-status.md) during the same
dogfooding pass: `toElements` in `static/app.js` collapses every raw
`calls` edge between two currently-collapsed containers into one
representative edge (`edgesById`, lines 152-167). When several raw calls
map onto the same representative pair, the representative's `status` is
whatever the *first* raw call happened to carry — later calls only get
appended to `edge.data.calls`, never checked against the status already
set.

Node collapsing already solves the equivalent problem correctly:
`strongestDescendantStatusByAncestor` (same file, lines 171-180) walks
every descendant of a collapsed container and keeps the most severe status
via `statusRank`/`STATUS_RANK` (lines 12-17), the same ranking already used
to color collapsed file/class nodes. Edges never got the same treatment.

This directly undercuts [054](054-deleted-caller-edge-status.md) and ADR
016's premise: a `calls` edge's color is a first-class review signal a
reviewer reads at the collapsed level (ADR 015 makes collapse the default
everywhere), and clicking it lists the underlying calls (ADR 016 §3). If
the representative color depends on iteration order rather than severity,
a genuinely changed call (e.g. one leg now `DELETED` per 054) can render
as `UNCHANGED` simply because an unrelated `UNCHANGED` call to the same
collapsed pair happened to be inserted first — silently hiding exactly the
signal 054 just added.

## Decision

In `toElements`'s edge-building loop, after pushing a raw call onto
`edge.data.calls`, compare its status against the representative edge's
current status with the existing `statusRank` and keep the more severe one
— the identical comparison `strongestDescendantStatusByAncestor` already
performs for nodes, reusing the same `STATUS_RANK` table rather than a
second ranking scheme:

```js
edge.data.calls.push({ ... });
if (statusRank(e.status) < statusRank(edge.data.status)) edge.data.status = e.status;
```

## Alternatives considered

- **A second, edge-specific severity ranking** — rejected: `STATUS_RANK` is
  already the single shared status-severity vocabulary the codebase uses
  for node collapsing; a second one for edges would drift from it for no
  reason.
- **Move representative-edge computation server-side** — which containers
  are currently collapsed is pure client UI state (`userExpandedIds`),
  never sent to the backend, so the backend has no way to know which raw
  edges collapse onto which representative. `strongestDescendantStatusByAncestor`
  already lives in JS for exactly this reason. Keeping this fix in JS is
  consistent with that existing, working precedent, not a departure from
  ADR 005 (which is about deriving *new* signal from snapshot data — this
  is re-deriving an existing signal over client-only collapse state, the
  same category node collapsing already handles in JS).
- **Render N parallel edges instead of collapsing** — already considered
  and rejected in ADR 016 for calls edges (fights fcose's layout, adds
  clutter on top of ADR 015's already-denser default view). Not reopened.

## Consequences

- Representative `calls` edges reflect the worst status among the raw
  calls they stand for, consistent with how collapsed nodes already work.
- No backend/API change: every raw call's status already travels in
  `edge.data.calls` today; this only changes which one becomes the
  representative `edge.data.status`.
- **Known gap, not fixed here:** this repo has no JS test harness — no
  `package.json`, no test runner — and `strongestDescendantStatusByAncestor`
  itself ships without a test today. This ticket follows that existing
  precedent: fixed in JS, verified manually in the browser (per CLAUDE.md's
  UI-testing rule), not blocked on standing up JS test infrastructure.
  Doing so, if ever wanted, is a separate decision — it's a dev-tooling/
  dependency choice of its own, not a one-line-bugfix side effect.

## Out of scope

- Standing up JS test infrastructure (see Consequences).
- Parallel-edge rendering for multiplicity — already rejected in ADR 016,
  not reopened.
