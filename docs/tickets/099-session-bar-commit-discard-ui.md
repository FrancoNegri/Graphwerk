# 099. Session bar UI: commit message box + commit/discard buttons

Status: done
Decision: docs/decisions/037-bottom-session-bar-commit-discard.md

## Goal

The bottom bar (ticket 094) grows the review-closing controls: an editable
commit-message box that fills itself when a session completes, a Commit
button, and a Discard button.

## Acceptance criteria

- A text box in the bottom bar fills with `meta.commit_message` when a
  session completes. It is overwritten only when a *new* session finishes
  (tracked via the polled `session_id`) — routine graph refetches never
  clobber the reviewer's edits. With no mined message it stays empty with
  an inviting placeholder.
- **Commit** POSTs `/api/commit` with the box's current text; success
  shows the existing toast with the commit hash and clears the box; a 400
  (empty message, non-git base) surfaces the server's message inline.
- **Discard** asks for confirmation (it destroys the agent's staged
  work), then POSTs `/api/discard`; success clears the box; a 409
  (session running) surfaces inline.
- After either action the graph refreshes via the existing hash polling —
  no bespoke reload path.
- Both buttons are disabled while a session is running.
- Verified by eyeballing the served UI end-to-end per the project's JS
  practice; all logic beyond DOM wiring stays server-side.

## Likely files

- `static/index.html` — box + buttons in the bottom bar
- `static/app.js` — fill/overwrite rule, POSTs, disabled states
- `static/style.css` — bar layout for the new controls

## Out of scope

Endpoints (097/098), message mining (095/096), bar placement (094 —
prerequisite). Regenerate-message button (ADR 037 out-of-scope list).
