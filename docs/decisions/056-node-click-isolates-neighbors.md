# 056. Node click isolates its edge-neighborhood; edges become non-selectable so they don't clear it

Status: proposed
Date: 2026-07-20

## Context

Two paired UI requests against the current graph view (`static/app.js`,
Cytoscape), both scoped to Phase 2's "Scale UX ... so big repos open
readable" line rather than a detour:

1. **Clicking a node should hide everything not connected to it.** Phase 2
   already ships several declutter tools — collapse-by-default (ADR 002),
   the changed-only toggle (ticket 006), hide-tests (ADR 036), hover-reveal
   for grey edges (ADR 020) — but even with all of them on, a node's actual
   neighborhood can still be buried among sibling files/classes that have
   nothing to do with it. This serves docs/02's "structural context" pitch
   directly: the graph should show *where* a change sits and *what it
   touches*, and right now that's something the reviewer has to find by eye
   rather than something the tool hands them on click.

2. **Clicking an edge should not deselect the node.** This is only a
   correctness fix for (1): today, tapping a `calls`/`imports` edge — e.g.
   to open its edge-calls panel — silently undoes whatever focus a prior
   node click established, because Cytoscape's default single-selection
   model deselects a previously-selected element whenever another
   selectable element is tapped. Without this fix, (1) would collapse back
   to the full graph the moment the reviewer clicks an edge to inspect it,
   which defeats the point of isolating a neighborhood in the first place.

Both are pure client-side view state, same category as the existing
toggles (ADR 005: JS stays a thin presentation layer). Neither touches the
differ, `FileIndex`/`SymbolInfo`, staging, or apply — no invariant is at
risk, and this isn't a detour from the current roadmap phase.

## Decision

**Node click isolates its neighborhood** (`static/app.js`):
- Tapping a node computes a *keep set*: the tapped node itself, its
  compound ancestors (parent chain, so containing file/class boxes stay
  visible), its own descendants (so an expanded container's contents
  survive clicking the container), every node directly joined to it by an
  edge of either kind (`calls` or `imports`) currently present in the
  Cytoscape instance — regardless of that edge's own hover/pinned/unchanged
  display state, since the *node* relationship exists independent of
  whether the edge itself happens to be drawn right now — and each such
  neighbor's own compound ancestors (so a neighbor's containing box still
  renders).
- Every node outside the keep set is hidden (`display: none`, via a
  Cytoscape style class — the same mechanism ADR 020 already uses for
  `edge.revealed`/`edge.pinned`, not a `toElements()`/`renderGraph()`
  rebuild; see alternatives).
- Tapping empty canvas restores every node to visible, alongside the
  existing `clearDetails()`/`unpinAllEdges()` reset. Tapping a different
  node recomputes the keep set for the new selection.
- The keep-set/hidden state must survive a `renderGraph()` rebuild (e.g. a
  poll-triggered refresh while a node stays selected) the same way
  `pinnedEdgeIds` already reapplies after `renderGraph()` destroys and
  recreates the Cytoscape instance.

**Edges become non-selectable** (`static/app.js`, cytoscape element/style
config): set `selectable: false` on edges. Nothing in the app depends on
Cytoscape's own `edge:selected` styling — edge "current selection" is
already tracked separately via `selectedEdgeId` and CSS classes — so this
has no other effect, and it stops Cytoscape's default single-selection
model from silently deselecting the previously-tapped node when an edge is
tapped afterward.

## Alternatives considered

- **Full connected-component reachability instead of direct (1-hop)
  neighbors.** Matches the literal words "connected to it" more loosely,
  but on any reasonably-connected repo the whole component is most of the
  graph, so it declutters little — and it's inconsistent with every
  existing "connected" notion in this UI, which is already 1-hop only
  (hover-reveal's `node.connectedEdges()`, ADR 020; `pinEdges` on node tap).
  Rejected.
- **Implement isolation as a `toElements()`/`renderGraph()` filter, same
  mechanism as `changedOnlyView`/`hideTestsView`.** Consistent with those
  toggles, but those are low-frequency checkbox flips; node-click isolation
  fires on every click and every deselect. `renderGraph()` destroys and
  recreates the whole Cytoscape instance and reruns the `fcose` layout —
  doing that on every click would jank the view and risks reshuffling node
  positions each time. A class-based `display: none` toggle (matching how
  ADR 020 already hides/reveals edges) needs no layout rerun and is
  trivially reversible. Rejected in favor of the class-toggle approach.
- **Fix the edge-deselect problem with `selectionType: 'additive'`
  core-wide instead of making edges non-selectable.** Broader behavior
  change — it would also make node selection itself additive (shift-less
  multi-select), which nothing here asks for. Making edges non-selectable
  is the narrower fix and matches that edges already don't use Cytoscape's
  selection state for anything. Rejected.
- **Dim (opacity) unconnected nodes instead of hiding them.** ADR 013
  already rejected dimming for edge clutter in favor of hiding; same
  reasoning applies here, and the user's request is explicitly for
  invisibility, not dimming. Rejected.

## Consequences

- Every node click doubles as a "focus on this neighborhood" action, with
  no new toggle or control to learn — consistent with docs/02's "structural
  context" and "blast radius" framing.
- One more piece of transient view state (`isolatedNodeId` or equivalent)
  joins `selectedId`/`pinnedEdgeIds` and must be reapplied after
  `renderGraph()` rebuilds, same as `pinnedEdgeIds` already is — a ticket
  acceptance criterion, not a follow-up.
- Edges lose Cytoscape's native `:selected` state entirely. No current
  style rule keys off it (only `node:selected` exists), so this is a no-op
  everywhere else in the app today; a future feature that wants
  edge-selection styling would need to reintroduce it deliberately.
- Purely `static/app.js` (+ its inline Cytoscape style array) — no backend,
  no new dependency, no change to the differ/model/staging layers.

## Out of scope

- Any toggle to turn this behavior on/off, or an indicator ("N of M nodes
  hidden") — can be added later as its own ticket if reviewers want it off.
- Changing which edges are pinned/revealed while isolated — ADR 020's
  behavior (hover-reveal, click-pin) is unchanged; isolation only affects
  *node* visibility.
- Highlighting the neighborhood instead of hiding the rest, or multi-node
  isolation (shift-click to grow the keep set) — neither was asked for;
  file as a new decision if it comes up.
- Hiding a *neighbor's* own unconnected descendants when that neighbor is
  an expanded container — the keep set only reaches one level into a
  neighbor (its ancestors, for rendering), not its children. Revisit only
  if reviewers find an expanded neighbor's untouched siblings distracting
  in practice.
