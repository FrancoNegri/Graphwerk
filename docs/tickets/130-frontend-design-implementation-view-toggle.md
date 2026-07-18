# 130. Frontend "Design" / "Implementation" mode toggle

Status: ready
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

A single mode toggle filters the rendered graph to one domain (Design =
`doc` nodes, Implementation = `code` nodes, or an "All" default) and sets
the scope sent with the next spawned session (ticket 132) — one control
doing both jobs, per ADR 046.

## Acceptance criteria

- A new toggle/segmented control (alongside the existing changed-only/
  hide-tests/show-imports toggles) with three states: All / Design /
  Implementation.
- Design/Implementation filter rendered nodes+edges to `domain === "doc"`
  or `domain === "code"` (ticket 129's field) — same client-side filtering
  pattern as `setHideTestsView`/`setChangedOnlyView`.
- The current mode is sent as `scope` (`"design"` | `"implementation"` |
  omitted for All) on the next `/api/prompt` call.
- Render-only JS, no client-side computation beyond filtering on the
  existing `domain` field (ADR 005).

## Likely files

- `static/app.js` — new toggle state + filter function, prompt submit
  includes `scope`.
- `static/index.html` — toggle control markup.

## Out of scope

- `GraphNode.domain` itself (ticket 129, already done).
- Session-side enforcement of the scope (tickets 131, 132).
