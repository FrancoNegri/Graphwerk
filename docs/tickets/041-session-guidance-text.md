# 041. Session guidance text + round-trip attribution test

Status: ready
Decision: docs/decisions/012-rationale-session-guidance.md

## Goal

Define the standing instruction spawned sessions will be given, as a plain
Python constant, and prove its exact wording actually earns distinct
per-file/per-symbol rationale from the real miner — not just that it reads
well.

## Acceptance criteria

- `graphwerk/rationale/guidance.py` exports `SESSION_GUIDANCE: str`, asking
  the agent to end its work with a per-file summary: one line per changed
  file, naming the file path and key changed symbols, each stating *why*
  the change serves the request.
- A test builds a synthetic transcript whose final message follows the
  `SESSION_GUIDANCE` format (multiple files, distinct reasons per file) and
  feeds it through the real mention-attribution miner (ADR 006 pipeline,
  not a stub) — asserting each mentioned file/symbol gets its own distinct
  rationale string, not one shared line.
- If `SESSION_GUIDANCE`'s wording and the miner's matching rules ever drift
  apart (e.g. a miner regex tightens), this test is the one that fails.

## Likely files

- `graphwerk/rationale/guidance.py` — new, `SESSION_GUIDANCE` constant only.
- `tests/rationale/test_guidance.py` (or wherever rationale tests live) —
  new round-trip test.

## Out of scope

- Wiring `SESSION_GUIDANCE` into `SessionRunner` or `cli._serve` (tickets
  042, 043).
- Any change to the miner/attribution rules themselves (ADR 006 stands).
