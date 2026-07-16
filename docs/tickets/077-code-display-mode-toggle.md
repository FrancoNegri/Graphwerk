# 077. Sidebar toggle: code + changes vs. changes only

Status: done
Decision: docs/decisions/028-edge-calls-dropdowns-and-code-mode-toggle.md

## Goal

Add a sidebar-wide control, defaulting to today's behavior ("code +
changes" — full source with the diff overlaid), that a reviewer can switch
to "changes only" to shrink every visible code panel down to just the
added/removed lines, using the `op` classification `GraphNode.code` lines
already carry (ADR 007) — no new data, a display filter.

## Acceptance criteria

- A two-option control (e.g. radio pair or segmented buttons) sits in the
  sidebar, visible whether a node or an edge-calls panel is showing;
  default selection is "code + changes."
- Switching to "changes only" filters every currently-rendered code panel
  (node-details code section, and every dropdown body inside the edge-calls
  panel from ticket 076) to lines whose `op` is `"added"` or `"removed"`,
  dropping `"context"` lines.
- If filtering would leave a panel with zero lines, that panel falls back
  to rendering its full code instead of an empty box (the "genuinely
  unchanged node" case — ADR 004/007 unchanged nodes are all-context).
- Toggling the control re-renders whatever is currently open (the selected
  node's details, or an open edge-calls panel) without requiring the
  reviewer to reselect it — implies tracking the last-shown edge similarly
  to the existing `selectedId` pattern for nodes.
- Switching back to "code + changes" restores full source with the diff
  overlay, unchanged from today's behavior.
- Manual verification per this project's thin-JS/eyeball convention: toggle
  on a modified node, an added node, a deleted node, and an unchanged node
  (fallback case), plus an open edge-calls dropdown.

## Likely files

- `static/app.js` — add the toggle's state and wire it into `renderCode`
  call sites (`showDetails`, edge-calls dropdown bodies from ticket 076);
  track the last-shown edge for re-render on toggle.
- `static/index.html` — add the toggle control markup in the sidebar.
- `static/style.css` — style the toggle control.

## Out of scope

- Windowed/contextual "changes only" (a few context lines around each
  change) — noted as a possible follow-up in ADR 028, not built here.
- Persisting the toggle choice across page reloads.
