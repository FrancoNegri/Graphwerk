# 016. Color call edges by status; list what a collapsed edge represents

Status: proposed
Date: 2026-07-15

*Amended 2026-07-17 (audit F-003):* the `AFFECTED` branch of decision #1
(affected source → unchanged target ⇒ edge status `AFFECTED`) was removed
during implementation as an over-tagging bug — it painted *every* call out
of an affected node, including calls with no bearing on the change, commit
cfb4832. Current behavior: a `calls` edge takes its target's status when
that target is changed, and stays `unchanged` otherwise — no edge is ever
`affected`. Pinned by
`test_calls_edge_to_unrelated_target_from_affected_source_has_unchanged_status`.

## Context

Node status coloring (red/blue/grey/amber for modified/added/deleted/
affected) already exists and is one of the product's core review signals
(docs/02, "blast radius for humans": color affected-but-unchanged nodes so
the reviewer sees impact, not just edits). Today's dogfooding session asked
for the same treatment on `calls` edges — the edge itself should say
whether it leads into changed code, not just the node at either end.

The same session, now that ADR 015 makes collapse the default for classes
too, raised a second point: once several symbol-to-symbol `calls` edges
collapse onto the same class/file representative pair, `toElements`
dedupes them to one line (`seenEdgeIds`) and the fact that, say, class `A`
calls three different methods on class `B` disappears. Clarified during
scoping: the fix is not to draw parallel edges (adds clutter to an already
denser default view from ADR 015) but to let the reviewer click the
collapsed edge and see the individual calls it stands for.

Both serve "structural context" and "blast radius for humans" directly and
fit Phase 2's UX line; this is one decision because both are about making
a *single rendered edge* carry more of the truth it's currently hiding.

## Decision

1. **`GraphEdge` gains a `status: Status` field** (default `UNCHANGED`),
   computed server-side in `GraphService`, `calls` edges only:
   - if the target node's status is `MODIFIED`, `ADDED`, or `DELETED` →
     edge status = target's status (the edge leads into changed code).
   - else if the source node's status is `AFFECTED` and the target is
     `UNCHANGED` → edge status = `AFFECTED` (this edge is *why* the source
     is affected — the same relationship `_mark_affected` already
     computes, just also stamped onto the edge that caused it).
   - else → `UNCHANGED`.

   `imports` edges keep `status = UNCHANGED` always (out of scope below).
   This is graph-algorithm logic derived from data already in `Snapshot`
   (node statuses, edges), so it belongs in Python next to
   `_mark_affected`, not duplicated in `app.js` — consistent with ADR 005.

2. **`app.js` maps `edge.status` to line color** using the same `COLORS`
   table nodes already use, for `calls` edges only — pure style lookup,
   no computation, same pattern as the existing status→color mapping for
   nodes.

3. **Clicking a `calls` edge lists the underlying symbol-to-symbol calls
   it represents** in the review sidebar. `toElements` already knows,
   for each rendered representative edge, every raw `data.edges` entry
   that collapsed onto it (today it just discards all but the first via
   `seenEdgeIds`); instead it keeps the list and attaches it as edge data.
   A new `cy.on('tap', 'edge', ...)` handler renders that list (source →
   target labels) in a small sidebar section. Purely a client-side view of
   data already in the payload — the same category as the existing
   collapse/dedup logic, not a new business rule, so it stays in `app.js`
   per the established view-logic-in-JS split (ADR 013/014/015).

## Alternatives considered

- **Edge status computed client-side from node statuses already in the
  payload** — avoids a model/API change, but the `AFFECTED` case needs the
  same source/target set-difference `_mark_affected` already performs
  server-side; duplicating that rule in JS is exactly the kind of
  graph-algorithm logic ADR 005 says belongs in Python. Rejected.
- **Encode status as edge width/dash pattern instead of color** — avoids
  visually competing with node colors, but the reviewer already reads
  color as "status" everywhere else in the graph; a second visual
  vocabulary for the same concept adds a thing to learn for no real gain.
  Rejected.
- **Render N parallel edges for N collapsed calls** — shows multiplicity
  directly on the graph with no click required, but was already weighed
  and rejected during scoping: ADR 015 already increases default density
  (calls on, classes collapsed), and parallel edges between the same two
  chips fight with fcose's layout more than a click-to-list does. Settled,
  not deferred.

## Consequences

- `/api/graph`'s edge payload gains a `status` field; `static/app.js` is
  the only current consumer, so this is a safe, low-risk shape change.
- New Python logic needs pytest coverage in the service layer (target-
  changed, affected-source, and unrelated cases) — real business logic,
  not a display filter, so it gets real tests per ADR 005.
- The sidebar gains a small "underlying calls" list that only appears for
  `calls` edges with more than one collapsed call behind them.
- Only `calls` edges carry meaningful status; `imports` edges are
  unaffected, which is a deliberate asymmetry (see out of scope).

## Out of scope

- Status coloring for `imports` edges — deferred; revisit only if
  dogfooding specifically asks for it (today's ask was calls only).
- Parallel-edge rendering for multiplicity — rejected above, not deferred.
- Persisting which edges/calls the reviewer has already inspected.
