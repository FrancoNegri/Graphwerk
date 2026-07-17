# Audit

A persistent record of graphwerk's consistency audits: what's been checked,
what's been found, and what's still open. Written and maintained by the
`audit` skill. Bug/inconsistency findings get filed as tickets under
`docs/tickets/` (implemented by the `ticket` skill, same as any other
ticket); missing-test findings stay queued here for the `audit-tests` skill
to work through directly.

Unlike `docs/decisions/` and `docs/tickets/`, this isn't a plan written once
and then implemented — it's a ledger that gets re-read and updated every
run. Findings persist across runs by ID: a run either confirms a finding is
still open, marks it resolved, or opens a new one. IDs are never reused,
even for resolved or wontfix findings, so history stays traceable.

## Findings ledger

| ID | Category | Status | Location | Summary | First seen | Ticket / Test |
|----|----------|--------|----------|---------|-------------|----------------|
| F-001 | bug | ticketed | `graphwerk/session.py::SessionRunner.status/_settle` | Concurrent status polls can double-enter `_settle` → AttributeError/500 at session end | [001](runs/001-2026-07-17.md) | [086](../tickets/086-sessionrunner-settle-race.md) |
| F-002 | bug | ticketed | `graphwerk/rationale/transcript.py::_bash_deleted_rel_paths` | Relative `rm` tokens (`./x.py`, `a/../b.py`) kept unnormalized, so deletion rationale keys never match differ paths | [001](runs/001-2026-07-17.md) | [087](../tickets/087-normalize-bash-deletion-paths.md) |
| F-003 | inconsistency | ticketed | ADR 016 / ticket 049 vs `service.py::_mark_edge_status` | Affected-edge rule deliberately removed in code (cfb4832) but ADR/ticket still state it | [001](runs/001-2026-07-17.md) | [088](../tickets/088-record-shipped-deviations-adr-016-020.md) |
| F-004 | inconsistency | ticketed | ADR 020 / ticket 058 vs `static/app.js:280` | Docs say wheelSensitivity was lowered to ~0.15–0.2; shipped value is 5, unrecorded | [001](runs/001-2026-07-17.md) | [088](../tickets/088-record-shipped-deviations-adr-016-020.md) |
| F-005 | inconsistency | ticketed | `docs/tickets/README.md`; tickets 078–080 | Status bookkeeping stale: README rows 049/060–064 vs ticket files; 078–080 implemented but marked ready | [001](runs/001-2026-07-17.md) | [089](../tickets/089-sync-ticket-statuses.md) |
| F-006 | missing-test | open | `graphwerk/apply.py` + `/api/apply`, `/api/reject` | The only code path that writes the developer's tree has zero test coverage (incl. path-escape check) | [001](runs/001-2026-07-17.md) | queued for audit-tests |
| F-007 | missing-test | open | `graphwerk/service.py::state_hash` | No behavioral test of the polling contract (stable when idle, changes on touch/add/delete) | [001](runs/001-2026-07-17.md) | queued for audit-tests |

## Runs

| # | Date | Commit | Opened | Resolved |
|---|------|--------|--------|----------|
| [001](runs/001-2026-07-17.md) | 2026-07-17 | 4beff12 | 7 (2 bug, 3 inconsistency, 2 missing-test) | 0 |
