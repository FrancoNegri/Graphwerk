# 156. Remove the reject-comment UI affordance

Status: done
Decision: docs/decisions/057-sidebar-code-scroll-drop-reject-ui.md

## Goal

The sidebar's actions section no longer offers the structured
reject-with-comment box; re-prompting the agent about a change happens
through the existing prompt bar instead.

## Acceptance criteria

- `#reject-box` (the `#reject-comment` textarea and `#btn-reject` button)
  is removed from `static/index.html`.
- `#reject-result` (the payload-preview block shown after a reject) is
  removed too — nothing can trigger it once `btn-reject` is gone.
- `static/app.js`'s `rejectNode()` function and the `reject-box`/
  `reject-result`/`btn-reject` wiring in `showDetails()` (app.js:712-714)
  are removed as dead code.
- `#actions` still renders `#btn-apply` correctly with no other regression
  to the approve/unapprove flow.
- No frontend code references `/api/reject` afterward.

## Likely files

- `static/index.html` — drop `#reject-box` and `#reject-result` (currently
  index.html:77-86).
- `static/app.js` — drop `rejectNode()` (app.js:806-828) and the three
  `reject-box`/`reject-result`/`btn-reject` lines in `showDetails()`
  (app.js:712-714).
- `static/style.css` — drop any rule that becomes unused as a result (check
  before removing — `.danger` and `textarea` styling are shared with
  `#btn-discard`/`#commit-message` and must stay).

## Out of scope

- Removing the backend `/api/reject` endpoint, `RejectRequest`, or
  `ApplyEngine.reject` — left in place per the ADR, for Phase 3 to
  repurpose or delete once real node-scoped session-resume is designed.
