# 089. Sync ticket statuses with reality (README rows + tickets 078–080)

Status: ready
Decision: docs/audit/runs/001-2026-07-17.md

## Goal

The ticket ledger stops lying about what's shipped (audit finding F-005).
Two layers of drift: `docs/tickets/README.md` rows for 049 and 060–064 say
`ready` while the ticket files themselves say `done`; and tickets
078/079/080 are fully implemented (commit 77da27a; dashed
collapsed-deleted rule at `static/app.js:351`; green/red palette;
`--danger` decoupling in `style.css`) but both their files and README rows
still say `ready`. Anything that picks "the next ready ticket" would
re-implement shipped work.

## Acceptance criteria

- README rows 049, 060, 061, 062, 063, 064 read `done`, matching their
  ticket files.
- Ticket files 078, 079, 080 read `Status: done`, and their README rows
  match — after spot-checking each one's acceptance criteria against the
  code (all three verified in the audit run; re-verify while editing).
- No other row or file changes.

## Likely files

- `docs/tickets/README.md` — the status column is the wrong side.
- `docs/tickets/078-collapsed-deleted-pill-dashed-treatment.md`,
  `079-modified-status-turns-green.md`,
  `080-decouple-prompt-error-color.md` — Status lines.

## Out of scope

- Tickets 008, 009, 054 — genuinely still open; untouched.
- Any process change to prevent future drift (worth raising separately if
  it recurs in the next audit run).
