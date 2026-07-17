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

*(empty — no audit run yet)*

## Runs

| # | Date | Commit | Opened | Resolved |
|---|------|--------|--------|----------|

*(empty — run the `audit` skill to create `runs/001-<date>.md`)*
