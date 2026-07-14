# 006. "Changed + blast radius only" view toggle

Status: done
Decision: docs/decisions/001-phase-2-real-session.md

## Goal

On a real repo the reviewer can flip to seeing only what the change touches:
changed nodes, affected (yellow) nodes, their parent files, and the edges
among them.

## Acceptance criteria

- A visible toggle control in the UI; off by default.
- When on: nodes with status unchanged (and not affected) are hidden, except
  parents of visible nodes (a file stays visible if any child is visible);
  edges with a hidden endpoint are hidden.
- When off: the full graph is restored, including edges.
- The toggle state survives the poll-driven graph refresh.
- Pure client-side: no API or backend changes.

## Likely files

- `static/app.js` — filter logic + toggle state
- `static/index.html`, `static/style.css` — the control

## Out of scope

Server-side filtering; per-node manual hiding; interaction with collapse
state beyond "both can be active without errors".
