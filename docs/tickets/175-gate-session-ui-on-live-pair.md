# 175. Gate prompt box + polling on the selected pair being live

Status: done
Decision: docs/decisions/060-comparison-picker-any-ref-vs-any-ref.md

## Goal

Depends on ticket 174. When the selected `staged` side isn't the working
directory, there's no live session to prompt and nothing that can change —
per ADR 060 this should read as a plain read-only history view: the prompt
box hides, and `/api/hash` polling (and the session-status polling that
rides along with it, `pollHashAndSession` in `static/app.js`) stops.
Switching `staged` back to the working directory restores both.

## Acceptance criteria

- `static/app.js` hides the prompt box (and any reject/session-status
  affordance) whenever the currently selected `staged` value isn't the
  working-directory token.
- `pollHashAndSession`'s polling loop stops issuing `/api/hash` requests
  while `staged` isn't the working directory, and resumes when it's
  switched back.
- Manually verified against the running demo server: selecting a
  historical commit on the compare-to dropdown hides the prompt box and
  the network tab shows no further `/api/hash` polling; switching back to
  "uncommitted" restores both.

## Likely files

- `static/app.js` — prompt-box visibility + polling gate.

## Out of scope

- Any backend change — `/api/prompt` and `/api/session` are untouched
  (ADR 060: they stay tied to the one live `SessionCycle` regardless of
  what's being viewed; this ticket only changes whether the frontend
  *shows*/*polls* them).
