# 163. Sync `docs/decisions/README.md`'s Status column with the ADR files

Status: done
Decision: docs/audit/runs/002-2026-07-21.md

## Goal

`docs/decisions/README.md`'s Status column stops disagreeing with the ADR
files it's summarizing (audit finding F-008).

## Acceptance criteria

- ADR 001's README row reads `accepted`, matching
  `docs/decisions/001-phase-2-real-session.md`'s own `Status:` line.
- ADR 021's README row reads `accepted`, matching
  `docs/decisions/021-src-layout-grouping.md`'s own `Status:` line.
- No other row changes — every other ADR file's own `Status:` line already
  matches its README row (verified this run by diffing all 58).

## Likely files

- `docs/decisions/README.md` — the table is the wrong side; the ADR files
  themselves are correct.

## Out of scope

- The broader pattern of ADRs marked `proposed` in both the file and the
  README despite having fully-shipped tickets — that needs per-ADR
  judgment (fully shipped vs. partially superseded), not a mechanical
  sync, and is a process question ticket 089 already deferred once.
