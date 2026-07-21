# 165. Relabel `/api/graph`'s base/staged paths in the UI

Status: done
Decision: docs/audit/runs/002-2026-07-21.md

## Goal

The UI's paths line describes what `/api/graph`'s `base` and `staged`
fields actually are post ADR 058, instead of the retired two-directory
labels (audit finding F-010).

## Acceptance criteria

- `static/app.js`'s paths line no longer reads
  `agent workspace: <dir><br>your tree: <ref>` — `data.staged` is the one
  repo directory the developer and the agent share, and `data.base` is a
  git ref (often a commit sha), not a second tree. The new copy should
  read naturally for both (e.g. "reviewing `<repo>` against `<ref>`" or
  similar — exact wording is the implementer's call).
- `graphwerk/server.py`'s comment above the `/api/graph` payload
  ("ticket 158 revisits this payload shape...") is removed or replaced
  with whatever's accurate now — ticket 158 didn't touch this payload
  shape (it was already correct from ticket 157), so the comment
  shouldn't keep pointing at a ticket that's since landed without
  touching it.

## Likely files

- `static/app.js` — the `paths` div's innerHTML line in `loadGraph()`.
- `graphwerk/server.py` — the stale comment on `/api/graph`.

## Out of scope

- Any other payload field or endpoint.
- The `approved`/apply/commit/discard UI — that's ticket 160.
