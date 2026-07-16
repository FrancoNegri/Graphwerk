# 066. Parse the guidance bullet format as the primary rationale source

Status: done
Decision: docs/decisions/025-rationale-mention-confidence.md

## Goal

When a transcript segment matches the `SESSION_GUIDANCE` bullet format
(`graphwerk/rationale/guidance.py`) — `` - `path/to/file.py` (`Symbol`, ...): reason ``
— parse it directly into per-file and per-symbol rationale, and give that
result priority over the generic mention-scanning in `attribute_files`/
`attribute_symbols`. A file's own dedicated bullet must never be shadowed
by a later segment that merely repeats its filename in passing.

## Acceptance criteria

- A new parser recognizes the guidance bullet shape and extracts, per
  matching line: the file path, the optional parenthesized symbol list,
  and the reason text after the colon.
- `RationaleStore._mine_transcript` uses bullet-parsed rationale for a
  file/symbol whenever one exists, before falling back to prose
  mention-scanning or proximity fallback for anything left unattributed.
- Reproduces the dogfood fix: given the agendabot session's actual
  segments 25-34 (one bullet per file, plus a trailing "Compatibility
  note" paragraph that re-mentions several filenames), `business_cache.py`,
  `webhook.py`, and `conversation.py` each resolve to their own bullet's
  text, not the compatibility note.
- A segment that isn't in the bullet shape (plain prose) is left to the
  existing mention/fallback logic unchanged.

## Likely files

- `graphwerk/rationale/attribution.py` — new bullet-format parser.
- `graphwerk/rationale/miner.py` — `_mine_transcript` priority ordering.
- `tests/rationale/test_attribution.py` — bullet-parsing cases, including
  the "dedicated bullet must beat a later trailing mention" case.

## Out of scope

- Tightening the prose-mention fallback itself (ticket 067) — this ticket
  only adds the higher-priority structured source in front of it.
- Confidence tracking (ticket 068).
