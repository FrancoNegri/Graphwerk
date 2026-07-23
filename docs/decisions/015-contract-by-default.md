# 015. Contract every container by default; show calls out of the box

Status: proposed
Date: 2026-07-15
Supersedes: 002

## Context

ADR 002 made unchanged files start collapsed but changed/blast-radius files
start expanded, on the theory that files needing review should stay open.
ADR 013/014 then added `imports`/`calls` edge toggles, both off by default,
to keep the initial view uncluttered.

Today's dogfooding feedback pushes further: "now I can't see no deps or
calls, I would like to see only calls" (already answered by ticket 046) and,
in the same session, "all the nodes should be contracted" — even the ones
ADR 002 auto-expands today. With calls edges now easy to turn on and classes
sitting inside files as their own compound boxes, a fully-open changed file
gets busy fast. The reviewer wants the *first* screen to be a tidy field of
colored chips they drill into, not a pre-expanded tangle they have to fold
closed.

This is still Phase 2's "Scale UX ... so big repos open readable" line —
the same goal ADR 002 served, just tightened by real use.

## Decision

1. **Collapse is uniform: every container starts collapsed, no exceptions.**
   Drop ADR 002's "changed/blast-radius files start expanded" rule. A node
   is expanded only if the user has explicitly double-clicked it open in
   this session; there is no longer a status-driven default. This makes
   `userCollapsedFileIds` (now redundant — collapsed is the ambient state)
   unnecessary; only `userExpandedFileIds` (renamed `userExpandedIds`)
   still needs tracking.

   This doesn't hide the change signal: a collapsed chip already renders
   in its `collapsedStatus` color (red/blue/grey/amber), so "does this
   file/class need my attention" is answerable without opening it — the
   same reasoning that made ADR 002's auto-expand policy useful is now
   satisfied by chip color instead of expansion state.

2. **Collapse generalizes from files to any container**, i.e. any node
   that is another node's `parent` — today that's `file` and `class`.
   `representativeId`'s ancestor walk in `toElements` is already
   kind-agnostic; it only needs the container-id set (renamed
   `collapsedContainerIds`) to include class ids, not just file ids. The
   dbltap-to-toggle listener widens from `node[kind='file']` to
   `node[kind='file'], node[kind='class']`, and the collapsed-chip style
   rule (`[collapsedStatus]`) drops its `[kind='file']` restriction so a
   collapsed class renders the same uniform chip a collapsed file does.
   Functions/methods have no children and stay uncollapsible.

3. **`show-calls` defaults to checked**, `show-imports` stays unchecked.
   Dogfooding wants call structure visible immediately; import edges are
   denser (file-to-file, not symbol-to-symbol) and stay opt-in as ADR
   013/014 already decided. This is a default-value flip on an existing
   mechanism, not a new one.

All three are presentation logic in `static/app.js`/`static/index.html`.
No backend or model change.

## Alternatives considered

- **Keep ADR 002's auto-expand for changed files, only add class-level
  collapse** — smaller diff, but doesn't address today's actual complaint
  (contracted files still pop open once they contain a change), and the
  auto-expand policy's original justification is now redundant now that
  collapsed chips carry status color.
- **Make the default configurable** (a "start expanded" flag/URL param) —
  more flexible, but no other toggle in the app persists or parameterizes
  its default; ADR 013/014 both rejected persistence for the same reason.
  Adding config surface for one policy while every other toggle stays a
  simple checkbox is inconsistent for no demonstrated need.

## Consequences

- Big graphs open as a uniform field of colored chips (file *and* class
  level); drilling into any one of them is a double-click, matching the
  "Scale UX" exit criterion.
- ADR 002's status-driven expand policy is superseded; its rationale
  ("changed files shouldn't be hidden") now rests entirely on chip color.
- Class nodes gain the same collapse affordance and styling files already
  have — one interaction model for every container kind instead of two.
- Touches no invariant: no backend/model change, JS stays presentation-only
  view state (same category as the existing toggles), consistent with ADR
  005 (server-side layers, thin JS).

## Out of scope

- Persisting expand/collapse state across page reloads (no toggle persists
  today; unchanged here).
- Method-level collapse (methods have no children — nothing to collapse).
- Coloring call edges by status, and listing the individual calls a
  collapsed edge represents — real, but a separate decision: see ADR 016.
