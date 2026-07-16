# 076. Fuse each edge-calls pair into a collapsed dropdown

Status: done
Decision: docs/decisions/028-edge-calls-dropdowns-and-code-mode-toggle.md

## Goal

Clicking a `calls` edge currently shows a flat `source → target` label
list, then a separate deduped wall of code below it. Replace this with one
native `<details>` element per call pair — closed by default — whose
summary is the `source → target` label and whose body is that pair's
caller/callee code, so the label and its code are the same disclosure
instead of two disconnected sections.

## Acceptance criteria

- `showEdgeCalls` renders one `<details>` per entry in the edge's `calls`
  list (not deduped by node id); each starts closed (no `open` attribute).
- Each `<details>`'s `<summary>` is the existing `qualifiedLabel(source) →
  qualifiedLabel(target)` text.
- Each `<details>` body renders the source symbol's code panel followed by
  the target's, via the existing `renderCode`/`nodesById` lookup — same
  per-node "skip if no code" guard that exists today.
- The old separate label-list (`#d-calls-list`) and deduped code block
  (`#d-calls-code`) markup/logic are removed or merged into the new
  structure — no leftover dead markup.
- `uniqueCallNodeIds` is deleted if this ticket removes its only caller;
  otherwise left alone.
- A test (or manual verification per this project's thin-JS/eyeball
  convention — no JS test harness) confirms: opening the edge-calls panel
  shows N closed dropdowns for N call pairs, each expandable independently.

## Likely files

- `static/app.js` — rewrite `showEdgeCalls`; remove `uniqueCallNodeIds` if
  it becomes dead.
- `static/index.html` — edge-calls section markup (`#edge-calls`) changes
  from separate list/code containers to a single dropdown-list container.
- `static/style.css` — style the `<details>`/`<summary>` to match existing
  sidebar section styling (chevron affordance, spacing).

## Out of scope

- The sidebar-wide code-display toggle (code+changes vs. changes only) —
  ticket 077.
- Any change to which raw calls collapse onto one container edge, or to
  edge status coloring (ADR 016) — untouched.
