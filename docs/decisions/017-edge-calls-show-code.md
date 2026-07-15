# 017. Clicking a calls edge shows caller/callee code, not just labels

Status: proposed
Date: 2026-07-15

## Context

Ticket 051 (ADR 016 decision #3) made clicking a `calls` edge list the
underlying symbol-to-symbol calls it collapsed, as plain text labels
(`PaymentValidator.charge → Gateway.send`). Today's dogfooding feedback:
"edges show the relation but I'd like to see code + diffs of callers and
callees" — the label tells the reviewer *that* a call exists, not *what*
the caller or callee actually does, which is the question a reviewer
following a call edge is actually trying to answer (docs/02: "structural
context... which callers are affected"; ADR 004's whole premise is that a
reviewer shouldn't hit a dead end at an unchanged node).

The data already exists: ADR 004 threads full source onto every
`GraphNode`, and ADR 007 upgraded that to `GraphNode.code` — a merged
line view with the diff overlaid and syntax highlighting, rendered
client-side by the existing `renderCode()` function. Getting from a
label to that view today requires closing the edge-calls panel,
possibly expanding one or two collapsed containers, and clicking the
specific symbol node — several steps to answer a question the edge click
was already trying to answer.

This is Phase 2 "Scale UX" territory (the same phase ADR 015/016 served)
and a direct continuation of ADR 016 decision #3, not a new area.

## Decision

Extend `showEdgeCalls` (`static/app.js`) so the edge-calls sidebar
section renders code, not just labels:

1. Walk the edge's `calls` list (source/target id pairs) and collect the
   **unique** node ids involved, in first-seen order. Class-level
   collapse (ADR 015) is exactly the case that produces multiple calls
   on one edge, and several of those pairs commonly share a caller or a
   callee (e.g. `A` calling three different methods on `B`) — dedup by
   id so that symbol's code renders once, not once per pair it appears
   in.
2. For each unique id, look it up in the existing `nodesById` map and
   render a small heading (`qualifiedLabel`, already used for the label
   list) followed by `renderCode(node.code)` — the exact function the
   node details panel already uses. No new rendering path.
3. Keep the existing source → target label list above the code panels,
   unchanged, as a compact index of which calls collapsed here — it's
   cheap and orients the reviewer before they scroll into code.

Purely a client-side view assembled from data already in the payload
(`node.code` per ADR 007, `calls` per ticket 051) — the same category as
the label list it extends, so it stays in `app.js` per the established
view-logic-in-JS split (ADR 005/013/014/015/016). No backend or model
change.

## Alternatives considered

- **Click a label to jump to that node's details panel** (reuse
  `showDetails` instead of adding code panels here) — smaller diff, and
  reuses the single-node view as-is, but only shows one side of a call
  at a time and costs an extra click per symbol; the label list already
  exists specifically to summarize the relation, so this would still
  leave the "read the code" step gated behind more clicks. Rejected —
  the user explicitly wants callers *and* callees visible together.
- **Side-by-side two-column layout for caller/callee code** — closer to
  a conventional diff-review layout, but the sidebar is a single narrow
  column everywhere else in the app (details panel included); a
  two-column special case for this one section adds CSS surface for a
  presentation need not asked for. Stacked panels match the existing
  layout and are simpler. Rejected.
- **Render one code panel per call pair (no dedup)** — simplest
  implementation, but directly regresses the motivating case from ADR
  016 (one class calling three methods on another) into three duplicate
  copies of the caller's code. Dedup by id is barely more code and
  avoids that. Rejected.

## Consequences

- Following a `calls` edge answers "what does the caller do, what does
  the callee do, does the change make sense" without leaving the edge
  click — a real widening of the review surface, same category of win
  as ADR 004.
- No payload change: `node.code` already ships on every node (ADR 007);
  this only changes what `app.js` does with data it already has.
- Long code panels for edges collapsing many distinct symbols are
  possible (e.g., a class with many collapsed methods) — same accepted
  tradeoff ADR 004/007 already made for full-file code views (no
  pagination), not a new one.

## Out of scope

- Any equivalent treatment for `imports` edges — imports carry no
  per-symbol code to show (file-to-file), consistent with ADR 016's
  imports exclusion.
- Side-by-side / diff-style dual-column layout — rejected above, not
  deferred.
- Jump-to-node-on-graph from the edge-calls panel (highlighting the
  caller/callee chip in the canvas) — real but separate, revisit only if
  asked.
