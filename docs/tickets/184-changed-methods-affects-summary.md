# 184. Sidebar: "Affects" summary line in changed-methods mode

Status: done
Decision: docs/decisions/062-variable-symbols-and-changed-method-blast-radius.md

## Goal

In `changed-methods` code-view mode, each rendered changed method shows a
compact line naming its enclosing class (with status) and any variables it
`uses` (with status) — the concrete payoff of ADR 062: seeing what a
changed method touches without leaving the code panel.

## Acceptance criteria

- `renderChangedMethods` (`static/app.js`) renders, under each changed
  method's heading, an "Affects:" line listing:
  - the method's enclosing class node (label + status chip), when the
    method's `parent` resolves to a `class`-kind node; omitted for a
    top-level function with no class parent.
  - every `variable`-kind node reached via a `uses` edge whose source is
    this method (label + status chip), deduplicated; omitted entirely
    (no "Affects:" line at all) when there is nothing to list.
- Status chips reuse the existing chip styling/classes already used
  elsewhere in the sidebar (`class="chip ${status}"`).
- This line is additive to the existing per-method code rendering — the
  method's own code view is unchanged.
- Works when `changed-methods` mode falls back to `full` (ADR 051's
  fallback for leaf/no-changed-descendant selections) — i.e., this ticket
  only touches the `renderChangedMethods` path, not the `full`-mode
  fallback path.

## Likely files

- `static/app.js` — `renderChangedMethods`, plus a small helper to look up
  a node's `uses`-edge targets from `graphData.edges` (mirroring how
  `changedLeafDescendants` already walks `graphData.nodes`).

## Out of scope

- Any change to which methods `changed-methods` mode selects — only what's
  additionally shown per selected method.
- Backend changes — this ticket is pure consumption of `uses` edges and
  `variable`/`class` nodes already in the payload (tickets 180-183).
