# 013. Import/call edges hidden by default behind a toggle

Status: proposed
Date: 2026-07-15

## Context

The graph renders two edge kinds unconditionally: `imports` (file-to-file)
and `calls` (symbol-to-symbol), per `graphwerk/models.py` `GraphEdge.kind`
and styled always-on in `static/app.js` (~lines 270-283). Feedback from
today's prompt-box dogfood run: with both edge kinds always drawn alongside
every file/class/function node, the graph is hard to read — the structural
context these edges provide (docs/02, "Structural context") stops paying
for itself once edge density crosses a threshold, well before a repo is
large enough to need the Phase 2 "changed + blast radius only" toggle
(ticket 006) to help.

This is *not* the "change-dependency edges" feature docs/02 calls the
killer feature — that's a different, not-yet-built thing (Phase 4:
dependency edges *between staged changes*, driving "apply group"). Today's
`imports`/`calls` edges are the whole-codebase structural graph, always
present since v1. Nothing about that later feature is touched by this
decision.

Current phase is Phase 2 (roadmap: "Scale UX ... so big repos open
readable") — this is squarely a legibility fix for that goal, not a
detour.

## Decision

Add a single checkbox, **"show deps + calls"**, unchecked by default,
alongside the existing `changed-only` / `hide-tests` toggles in
`static/index.html`. Wire it exactly like those two:

- `static/app.js` gains a `showEdgesView` boolean (default `false`) and a
  `setShowEdgesView(enabled)` setter that re-renders from the already-held
  `graphData`, same shape as `setChangedOnlyView` / `setHideTestsView`.
- The element-building step (`toElements`, ~app.js line 88) drops edges
  whose `kind` is `imports` or `calls` unless `showEdgesView` is true.
  Nodes are untouched — this only ever filters edges.
- No server or model change: `GraphEdge.kind` already carries the
  information needed; this is a pure display filter over data the client
  already has, matching how `hide-tests` filters already-delivered nodes.

## Alternatives considered

- **Server-side edge filtering (query param on `/api/graph`)** — would let
  the server skip serializing hidden edges, but adds a request-shape
  variant for what is purely a display preference, and edge volume at
  today's scale (3632 edges on the Flask benchmark, ~1s `/api/graph`) isn't
  a payload-size problem worth optimizing. Rejected — contradicts ADR 005
  ("JS stays thin" is about layout math, not about who owns display-only
  filtering; the existing toggles already filter client-side for the same
  reason).
- **Dim instead of hide (opacity)** — keeps edges spatially present as a
  reminder they exist, but doesn't solve the stated problem (visual
  clutter from edge count), just softens it. Rejected; user asked for
  hidden by default with an explicit reveal.
- **Two independent toggles (imports vs. calls separately)** — more
  precise, but doubles the UI for a problem reported as one ("deps + calls
  make the graph difficult to read"). Deferred; see Out of scope.

## Consequences

- Default view gets less cluttered with zero backend work; existing
  `/api/graph` payload, tests, and perf numbers are unaffected.
- Reviewers who want the structural-context edges (docs/02's stated value
  of import/call edges) have to opt in every session (no persistence) —
  acceptable since the other two toggles behave the same way today.
- Sets the pattern for Phase 4's change-dependency edges to also default
  off if they turn out to add similar clutter once built.

## Out of scope

- Splitting into separate imports/calls toggles — add only if dogfooding
  shows one is wanted without the other.
- Persisting the toggle state across reloads — none of the existing
  toggles persist either; out until that's a real complaint.
- Any change to Phase 4's change-dependency-edges feature (unbuilt,
  unrelated).
