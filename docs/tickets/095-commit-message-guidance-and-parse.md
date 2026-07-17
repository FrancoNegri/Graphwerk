# 095. Commit-message line: session guidance + transcript parse

Status: done
Decision: docs/decisions/037-bottom-session-bar-commit-discard.md

## Goal

Spawned sessions are instructed to end with a `Commit-message: <one line>`
line, and the rationale layer can extract that line from a transcript.

## Acceptance criteria

- `SESSION_GUIDANCE` instructs the agent to close its final message, after
  the per-file bullets, with exactly one line of the form
  `Commit-message: <concise one-line summary of the whole change set>`.
- A parse function in the rationale package extracts that line's text from
  the final assistant segment of a transcript, returning `None` when
  absent, malformed, or empty after the prefix.
- Round-trip test in the existing guidance-test style: a synthetic
  transcript whose closing message follows the new guidance yields the
  commit message; a transcript without the line yields `None`.
- Existing bullet attribution is unaffected (existing rationale tests
  stay green).

## Likely files

- `graphwerk/rationale/guidance.py` — guidance text
- `graphwerk/rationale/attribution.py` (or `miner.py`, whichever fits the
  existing seams) — parse function
- `tests/rationale/` — round-trip + absence tests

## Out of scope

Exposing the message through `RationaleStore`/snapshot meta (ticket 096).
Any UI work.
