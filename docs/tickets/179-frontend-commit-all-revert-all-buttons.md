# 179. Frontend: commit-all / revert-all buttons

Status: done
Decision: docs/decisions/061-whole-tree-commit-all-revert-all.md

## Goal

Depends on ticket 178. Let the developer trigger the two new endpoints
from the graph UI, next to ticket 174's base/compare-to dropdowns.

## Acceptance criteria

- Two buttons render in the header, visible only when the selected
  `staged` is the working-directory token — the same gate ticket 175
  already applies to the prompt box/polling; hidden for historical pairs.
- "Commit all" is prefilled from the current snapshot's `commit_message`
  field (already in the `/api/graph` payload). Posting sends whatever's in
  the field as `message` to `/api/commit-all`; on success, re-renders the
  graph from the response (or refetches `/api/graph` if the endpoint
  doesn't return a full snapshot) instead of waiting for the next hash
  poll.
- "Revert all" shows a `window.confirm()` before posting to
  `/api/revert-all` (stash is recoverable but still a surprising thing to
  fire by accident); on success, re-renders/refetches the same way.
- Both surface the endpoint's error body (400s, etc.) through whatever
  error-display mechanism `static/app.js` already uses for `/api/prompt`
  failures, rather than failing silently.
- Manually verified against the running demo server
  (`.venv/bin/python -m graphwerk demo`): make an edit, click "commit
  all," confirm `git log` shows the new commit and the graph diff clears;
  make another edit, click "revert all," confirm `git stash list` shows
  the entry and the graph diff clears.

## Likely files

- `static/app.js` — button handlers, gating, refetch/re-render.
- `static/index.html` (or wherever ticket 174's dropdown markup lives) —
  the two buttons.

## Out of scope

- Message-editing beyond a plain text field.
- Any confirm-dialog styling beyond the browser default.
- Anything for historical (non-live) pairs — buttons stay hidden, per
  ADR 061/CLAUDE.md's "thin JS" rule (no JS test harness — verified by
  hand in the browser).
