# 070. Extend SESSION_GUIDANCE to cover deleted files

Status: done
Decision: docs/decisions/026-rationale-for-deleted-files.md

## Goal

`SESSION_GUIDANCE` currently only tells the agent how to narrate
added/modified files. Extend it so a file the agent deletes gets a line in
the same colon-based shape the guidance-bullet parser already understands
(ticket 066) — no parser change needed for a cooperative session.

## Acceptance criteria

- `SESSION_GUIDANCE` text includes an explicit instruction and example for
  deleted files, using the existing colon shape, e.g.
  `` - `path/to/old_file.py`: removed — reason ``.
- Round-trip test (mirroring ticket 041's pattern): a transcript segment
  following the new deletion-guidance shape is correctly parsed and
  attributed to that path via `parse_guidance_bullet`/
  `attribute_guidance_bullets`.

## Likely files

- `graphwerk/rationale/guidance.py` — `SESSION_GUIDANCE`.
- wherever ticket 041's round-trip test lives (guidance <-> attribution).

## Out of scope

- Parsing phrasing that doesn't follow this instruction (ticket 071) —
  this ticket only changes what the agent is asked to write.
