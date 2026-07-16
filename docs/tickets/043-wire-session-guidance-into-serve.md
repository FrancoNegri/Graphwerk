# 043. Wire `SESSION_GUIDANCE` into `cli._serve`'s `SessionRunner`

Status: done
Decision: docs/decisions/012-rationale-session-guidance.md

## Goal

Make spawned sessions (the prompt-box flow) actually receive the guidance
text end to end, while terminal-started sessions stay untouched.

## Acceptance criteria

- `cli._serve` constructs its `SessionRunner` with
  `system_prompt=SESSION_GUIDANCE` (imported from
  `graphwerk.rationale.guidance`).
- A test on the `_serve` wiring (or the CLI's existing SessionRunner
  construction test) asserts the runner it builds carries the guidance
  text — mirroring how existing `_serve` tests check other constructor
  args, no real subprocess spawned.
- No change to terminal-started session behavior (there's no runner
  involved there today).

## Likely files

- `graphwerk/cli.py` — `_serve`'s `SessionRunner(...)` construction.
- `tests/test_cli.py` (or equivalent) — new assertion on the wiring.

## Out of scope

- The guidance text itself (ticket 041) and the constructor parameter
  (ticket 042) — this ticket only connects the two.
- Any docs/README note for terminal-started sessions (ADR 012, Out of
  scope).
