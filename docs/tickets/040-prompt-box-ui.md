# 040. Prompt box + busy indicator in the UI

Status: done
Decision: docs/decisions/011-prompt-box-session-kickoff.md

## Goal

The user can kick off the agent from the graph page: type a prompt,
submit, watch the graph fill in — no terminal, no chat log.

## Acceptance criteria

- A prompt input + submit control in the page chrome; submit POSTs to
  `/api/prompt` and clears the box on acceptance.
- While `/api/session` reports `running` (polled on the same cadence as
  the existing `/api/hash` poll), the box is disabled and a busy
  indicator shows; `done` re-enables it; `failed` re-enables it and
  renders the server-provided error line (reuse the banner from ticket
  034 if it exists by then, otherwise a minimal inline message).
- A 409 (run already active) renders as the busy state, not an error.
- No agent output, transcript, or chat history is rendered anywhere —
  input box and status only (ADR 011 user constraint).
- JS consumes endpoint fields only; wording comes from the server.
  Verified by eyeballing the demo (submit with claude absent → failed
  message) and a real run in the agendabot setup (project testing
  convention).

## Likely files

- `static/index.html`, `static/app.js`, `static/style.css`

## Out of scope

- Reject-with-comment UI and resume flow (Phase 3).
- Prompt history/templates.
