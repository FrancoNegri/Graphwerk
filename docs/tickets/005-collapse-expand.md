# 005. Collapse/expand file nodes (double-click)

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md

## Goal

Big graphs become skimmable: a file's compound node can be collapsed to a
single node and re-expanded, by double-click.

## Acceptance criteria

- Double-clicking a file compound node collapses it: its child symbol nodes
  hide and the file renders as one node; double-clicking again expands it.
- A collapsed file still signals its contents' state (keeps the strongest
  child status color: changed > affected > unchanged).
- Edges into hidden children don't dangle — they disappear or reroute to
  the file node while collapsed.
- Collapse state survives the poll-driven graph refresh (`/api/hash`
  refetch) for files still present.
- If a plugin is used (e.g. cytoscape-expand-collapse), it is vendored via
  npm into `static/vendor/` and loaded like the existing vendor files —
  no CDN, no Node-side logic.

## Likely files

- `static/app.js` — interaction + state
- `static/index.html`, `static/vendor/` — plugin wiring if used

## Out of scope

The changed-only view toggle (ticket 006); persisting collapse state across
page reloads.
