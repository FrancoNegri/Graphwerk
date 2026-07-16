# 028. Collapsible per-call dropdowns; a sidebar toggle for code+changes vs. changes-only

Status: proposed
Date: 2026-07-16

## Context

Two related sidebar-legibility complaints from dogfooding, both Phase 2
"Scale UX" territory (the same phase ADR 013–020 served):

1. **The edge-calls panel reads oddly.** ADR 017/ticket 052 made clicking a
   collapsed `calls` edge render a flat `source → target` label list,
   followed underneath by a separate block of every unique symbol's code
   (deduped by id, per ADR 017 decision #1). The two pieces are visually
   disconnected: the label tells you a pair exists, then you have to scroll
   past it into an undifferentiated wall of code to find the pair you
   actually care about. There's no way to look at one relation without the
   others being in view too.
2. **There's no way to see only what changed.** ADR 004/007 made the
   sidebar always show full source with the diff overlaid in place — the
   right default for understanding a change in context, but a reviewer who
   already knows the file and just wants to re-check *what moved* has no
   way to shrink the view to only the touched lines. Every code panel
   (node details and edge-calls) always renders full source.

Both are pure display problems over data the payload already carries in
full (`GraphNode.code`, `calls` edge data) — no differ, model, or backend
change is implicated by either.

## Decision

Two independent, purely client-side (`static/`) changes:

**1. Fuse each call-pair label with its code, collapsed by default.**
Replace the flat label list + separate deduped-code block in
`showEdgeCalls` (`static/app.js`) with one `<details>` element per call
pair: `<summary>` is the existing `source → target` label, closed by
default (no `open` attribute — native HTML disclosure needs no JS to track
open/closed state), and the body renders the source symbol's code panel
followed by the target's (`renderCode`, unchanged). Dropping the ADR 017
node-level dedup is deliberate and enabled by this change: since a panel
only renders its code once a reviewer opens that specific pair, the
"class calling three methods on the same callee" case ADR 017 optimized
for no longer produces simultaneous duplicate walls of code — it produces
three collapsed rows, each cheap until opened. `uniqueCallNodeIds` is
removed as dead code.

**2. A sidebar-wide code-display toggle: "code + changes" / "changes only."**
A two-option control (default **code + changes**, i.e. today's behavior)
placed in the sidebar, above both the node-details and edge-calls panels
so it's visible regardless of what's selected. It drives one shared
filter applied wherever `renderCode` is called (node details' code
section, both panels inside each edge-calls dropdown): in "changes only"
mode, drop lines whose `op` is `"context"`, keeping only `added`/`removed`
lines — the classification `GraphNode.code` already carries per line
(ADR 007), so this is a filter over existing data, not a new computation.
**Fallback:** if filtering would leave zero lines (a genuinely unchanged
node — all-context by construction, ADR 004), render the full view
instead of an empty panel; there's nothing to hide on an unchanged node,
so "changes only" degrades to showing what's there.
The toggle is global UI state (like the existing `show-imports`/
`show-calls` checkboxes), not per-node: switching it re-renders whatever
panel is currently open. This requires tracking the last-shown edge
(mirroring the existing `selectedId` pattern for nodes) so `showEdgeCalls`
can be re-invoked on toggle change.

Both changes are JS/HTML/CSS only, consistent with the Python-everywhere/
JS-only-in-`static/` rule — no `graphwerk/*.py` file is touched by either.

## Alternatives considered

- **Per-pair dropdowns, keep node-level dedup** (render a placeholder link
  per pair that jumps to a shared, deduped code block below) — preserves
  the ADR 017 dedup optimization, but reintroduces the exact visual
  disconnect being fixed: the pair you clicked still isn't where its code
  appears. Rejected — the point is fusion, not indirection.
- **"Changes only" as a windowed diff** (show a few context lines around
  each change, like unified diff, instead of stripping context entirely) —
  more readable for some changes, but needs new logic to decide window size
  per change and isn't what was asked for. Noted below as a follow-up if
  the plain strip proves hard to read; not built now.
- **Per-panel toggle instead of one global control** — more flexible (mix
  full-source and changes-only across different open panels), but the
  request was for one sidebar button, and a single global toggle matches
  the existing view-state precedent (`changed-only`, `show-imports`,
  `show-calls` are all global, not per-node). Rejected as unrequested
  complexity.

## Consequences

- Easier: scanning many collapsed calls without an unreadable code dump;
  quickly re-checking just the diff on a large file without wading through
  unchanged surrounding code.
- Harder: nothing structurally new — both changes are filters/collapses
  over data already shipped; no payload growth, no new endpoint.
- Removes `uniqueCallNodeIds` (dead once dedup is dropped) — confirm no
  other caller depends on it before deleting (ticket-level detail).
- No invariant touched: no backend dependency, no hunk-to-symbol mapping,
  `FileIndex`/`SymbolInfo` untouched, all logic stays in `static/`.

## Out of scope

- Windowed/contextual "changes only" view (noted above) — revisit only if
  the plain strip-to-diff-lines view reads poorly in practice.
- Persisting the toggle choice across page reloads (`localStorage`) — easy
  addition, not asked for.
- Jump-to-node-on-graph from an opened edge-calls dropdown — already noted
  out of scope in ADR 017, unaffected here.
- Any change to which pairs collapse onto one edge, or to call-edge status
  coloring (ADR 016) — unrelated, untouched.
