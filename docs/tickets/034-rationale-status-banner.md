# 034. UI banner for rationale source status

Status: done
Decision: docs/decisions/009-rationale-fails-loudly.md

## Goal

When rationale is missing or misconfigured, the reviewer sees one plain
line saying so — instead of inferring it from an absent sidebar section.

## Acceptance criteria

- The server composes a single human-readable status message in
  `meta.rationale` (Python decides wording; pytest covers the cases):
  a warning if present (ticket 033), else a "no rationale source found for
  <staged root>" message when changed nodes exist but transcript and
  sidecar are both absent/empty, else no message.
- `app.js` renders the message, when present, as a dismissible one-line
  banner; no message → no banner. The JS reads the payload field only —
  no detection logic client-side (ADR 005 split).
- Demo instance shows no banner; the agendabot serve setup from the
  dogfood run shows the misplaced-session warning (eyeball verification,
  per project testing convention).

## Likely files

- `graphwerk/service.py` or `graphwerk/rationale/miner.py` — message
  composition
- `static/index.html`, `static/app.js`, `static/style.css` — banner element
- `tests/` — message-composition cases

## Out of scope

- Per-node "no rationale for this node" affordances in the sidebar.
- Server logging beyond the payload (fine to add a startup print, but the
  banner is the deliverable).
