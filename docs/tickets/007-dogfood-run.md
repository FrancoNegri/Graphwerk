# 007. Dogfood: review a real graphwerk change with graphwerk

Status: done (2026-07-14 — see Findings below; UI apply/reject exercised via
the exact endpoints/payloads the UI buttons send, per CLAUDE.md's curl-based
verification; a human browser pass over the same flow remains worthwhile)
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

## Findings (run of 2026-07-14)

What was run: `graphwerk start` on this repo (worktree auto-created, UI
served); a headless `claude` session in the worktree implemented `--version`
(cli.py + `__init__.py` + pyproject.toml) plus a reject-prompt reword in
apply.py; review happened against the live server.

- **Worked end to end.** Transcript auto-discovered from
  `~/.claude/projects/` (session started *after* the server — picked up on
  reload as designed). Node states correct throughout: modified symbols,
  cross-file affected blast radius, convergence to all-unchanged after
  apply + redo. Applied files landed in base intact: `graphwerk --version`
  prints `graphwerk 0.2.0`, full suite green (20 passed).
- **Reject loop validated beyond spec.** The recorded reject payload, fed
  manually to a fresh session in the worktree, made the agent revert exactly
  the rejected apply.py edit and nothing else — good evidence for the
  Phase 3 design.
- **Flask run (mid-size, 959 nodes / 3632 edges):** indexed and diffed
  correctly, sensible blast radius; `/api/graph` ~1s, `/api/hash` ~30ms —
  no perf work needed yet.
- **Ticket 008:** a staged file with a syntax error shows as every symbol
  `deleted` — misleading, and mid-edit saves make it common.
- **Ticket 009:** the staged pyproject.toml change never appeared in the
  graph, yet was appliable — non-Python changes are a review blind spot.
- **Roadmap note (Phase 5, pulled forward):** rationale mining attached one
  weak lead-in sentence to all six files because the session batched its
  edits; the real per-file "why" was in the final summary the miner ignores.
  Redesign is a `north-star` decision.
