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
| F-001 | bug | resolved | `graphwerk/session.py::SessionRunner.status/_settle` | Concurrent status polls can double-enter `_settle` → AttributeError/500 at session end | [001](runs/001-2026-07-17.md) | [086](../tickets/086-sessionrunner-settle-race.md) |
| F-002 | bug | resolved | `graphwerk/rationale/transcript.py::_bash_deleted_rel_paths` | Relative `rm` tokens (`./x.py`, `a/../b.py`) kept unnormalized, so deletion rationale keys never match differ paths | [001](runs/001-2026-07-17.md) | [087](../tickets/087-normalize-bash-deletion-paths.md) |
| F-003 | inconsistency | resolved | ADR 016 / ticket 049 vs `service.py::_mark_edge_status` | Affected-edge rule deliberately removed in code (cfb4832) but ADR/ticket still state it | [001](runs/001-2026-07-17.md) | [088](../tickets/088-record-shipped-deviations-adr-016-020.md) |
| F-004 | inconsistency | resolved | ADR 020 / ticket 058 vs `static/app.js:280` | Docs say wheelSensitivity was lowered to ~0.15–0.2; shipped value is 5, unrecorded | [001](runs/001-2026-07-17.md) | [088](../tickets/088-record-shipped-deviations-adr-016-020.md) |
| F-005 | inconsistency | resolved | `docs/tickets/README.md`; tickets 078–080 | Status bookkeeping stale: README rows 049/060–064 vs ticket files; 078–080 implemented but marked ready | [001](runs/001-2026-07-17.md) | [089](../tickets/089-sync-ticket-statuses.md) |
| F-006 | missing-test | wontfix | `graphwerk/apply.py` + `/api/apply`, `/api/reject` | The only code path that writes the developer's tree has zero test coverage (incl. path-escape check) | [001](runs/001-2026-07-17.md) | superseded by ticket 159 (deletes this code) |
| F-007 | missing-test | open | `graphwerk/service.py::state_hash` | Partial: markdown-edit case now covered; stable-when-idle and add/delete/python-edit cases still aren't | [001](runs/001-2026-07-17.md) | queued for audit-tests |
| F-008 | inconsistency | ticketed | `docs/decisions/README.md` vs ADR 001/021 files | Table Status column says `proposed`, ADR files say `accepted` | [002](runs/002-2026-07-21.md) | [163](../tickets/163-sync-adr-readme-statuses.md) |
| F-009 | inconsistency | ticketed | `graphwerk/rationale/miner.py::_misplaced_session_warning` | Dead code post ticket-158 (base_root==staged_root always); message still references deleted `--base`/`--staged` flags | [002](runs/002-2026-07-21.md) | [164](../tickets/164-drop-dead-misplaced-session-warning.md) |
| F-010 | inconsistency | ticketed | `static/app.js:80-81`, `graphwerk/server.py:62` | "agent workspace"/"your tree" labels now show a directory and a git ref respectively; stale comment promises a fix ticket 158 didn't make | [002](runs/002-2026-07-21.md) | [165](../tickets/165-relabel-graph-payload-paths.md) |
| F-011 | inconsistency | ticketed | `README.md` (intro, Quickstart, Layout, Status) | Describes retired apply/reject/worktree model across several sections; not in any of tickets 157-162's scope | [002](runs/002-2026-07-21.md) | [166](../tickets/166-resync-readme-with-adr-058.md) |

## Runs

| # | Date | Commit | Opened | Resolved |
|---|------|--------|--------|----------|
| [001](runs/001-2026-07-17.md) | 2026-07-17 | 4beff12 | 7 (2 bug, 3 inconsistency, 2 missing-test) | 0 |
| [002](runs/002-2026-07-21.md) | 2026-07-21 | bcbb889 | 4 (0 bug, 4 inconsistency, 0 missing-test) | 5 |
