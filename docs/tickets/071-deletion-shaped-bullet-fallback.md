# 071. Recognize a deletion-shaped guidance bullet as a fallback

Status: ready
Decision: docs/decisions/026-rationale-for-deleted-files.md

## Goal

Even when a session's closing narration doesn't follow the colon shape for
a deletion (ticket 070), still parse a reasonably-shaped deletion line as
that file's rationale — including transcripts already recorded before
ticket 070 landed.

## Acceptance criteria

- A new pattern recognizes `` - `path` → removed (...) `` (arrow-plus-
  "removed" shape, the one actually observed) as a deletion bullet,
  extracting the path and the remaining text as the reason.
- Tried only when `parse_guidance_bullet` (colon shape) doesn't match — the
  colon shape stays primary and unchanged.
- Reproduces the dogfood case: session `faf3bf05`'s segment —
  `` - `src/agendabot/webhook.py` → removed (converted to the package
  above; `agendabot.webhook:app` and all existing imports/monkeypatches
  keep working unchanged). `` — attributes to `src/agendabot/webhook.py`.

## Likely files

- `graphwerk/rationale/attribution.py` — new deletion-bullet pattern,
  wired into `attribute_guidance_bullets`.
- `tests/rationale/test_attribution.py`.

## Out of scope

- The guidance-text change (ticket 070).
- Bash-detected deletion events for prose-only mentions (ticket 072).
