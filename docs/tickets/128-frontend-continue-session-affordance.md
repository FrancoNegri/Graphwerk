# 128. Frontend: "continue this session" affordance

Status: ready
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

After a session completes, the prompt bar offers sending the next prompt
as a follow-up in the same session, alongside the existing implicit "new
session" behavior — the minimal UI needed for a real dialogue, without
introducing a chat log (ADR 011's "kickoff-only, no chat log" stance for
the code side is unchanged; this only adds a control, not a transcript
view).

## Acceptance criteria

- A checkbox/toggle next to the prompt input, e.g. "continue last
  session" — visible and enabled only when `session.session_id` is set
  and `session.state` is terminal (mirrors the existing
  `SESSION_BUSY_STATES` disabling logic already in `renderSessionState`).
- When checked at submit time, `/api/prompt` is called with
  `continue_session: true` (ticket 127); unchecked (default) is today's
  behavior, byte-for-byte.
- No new persistent history/log UI — this is a single control, not a
  message list.
- Render-only JS consuming fields already on the polled payload (ADR 005).

## Likely files

- `static/app.js` — prompt submit handler, new toggle wiring.
- `static/index.html` — new checkbox/toggle element near the prompt input.

## Out of scope

- `SessionCycle`/`server.py` changes (ticket 127, already done).
- Any transcript/chat-log view.
