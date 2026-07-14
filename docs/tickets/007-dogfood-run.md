# 007. Dogfood: review a real graphwerk change with graphwerk

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md

Depends on: tickets 001–006. This is a validation ticket (the Phase 2 exit
criterion), not a TDD ticket — its output is findings, not code.

## Goal

Prove the end-to-end loop: a graphwerk feature is implemented by a real
Claude session in the staging worktree and reviewed/applied through the
graphwerk UI.

## Acceptance criteria

- `graphwerk start` run on this repo; a real Claude Code session implements
  a small change in the staging worktree.
- The graph shows the staged change with correct node states, and the
  per-node "why" comes from the auto-discovered transcript (no `--transcript`
  flag).
- At least one node applied via the UI and one rejected, and the applied
  change lands correctly in the base tree.
- Run against at least one mid-size external repo; anything the
  indexer/differ/UI trips on is recorded as new ticket(s) or roadmap notes.
- ADR 001 status flipped to accepted (or findings say why not).

## Likely files

- `docs/tickets/` — follow-up tickets from findings
- `docs/04-roadmap.md` — notes on deferred findings

## Out of scope

Fixing nontrivial findings inline — they become their own tickets.
