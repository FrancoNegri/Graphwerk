# 117. Frontend: commit box driven by the polled cycle, not client memory

Status: ready
Decision: docs/decisions/042-regenerated-commit-message-per-cycle.md

## Goal

The commit-message box fills from `/api/session`'s `commit_message`
field, survives a page reload (server-held, so a fresh poll returns the
same value), and the box never goes stale mid-regeneration.

## Acceptance criteria

- `renderSessionState`/`maybeFillCommitMessageBox` fill the box from
  `session.commit_message` instead of `data.meta.commit_message`; the fill
  guard becomes "overwrite only when the polled value actually changed
  from what's currently shown" — no `completedSessionId`/
  `filledForSessionId`/`minedCommitMessage` session-id bookkeeping needed
  anymore (deleted).
- On a fresh page load, an in-progress or already-`done` cycle's message
  appears correctly with no extra client-side state required — verified
  by reloading mid-review against the served UI.
- `summarizing` is added to `SESSION_BUSY_STATES` with its own label
  ("writing commit message…"); prompt input, commit, and discard stay
  disabled through it, same as `running`/`checking`.
- `meta.commit_message` is no longer read anywhere in `app.js` (ticket 116
  removed it server-side).
- Verified by eyeballing the served UI per the project's JS practice:
  send a prompt, watch the bar progress through running → checking →
  summarizing → done with the box filling at the end; reload mid-cycle
  and after `done` and confirm the box is correct both times; send a
  second prompt and confirm the box keeps showing the first message until
  the second cycle's own regeneration replaces it.

## Likely files

- `static/app.js` — fill logic, busy states, dead-code removal

## Out of scope

Server-side generation/wiring (113-116). Any new UI beyond the label and
fill-source change — no new controls.
