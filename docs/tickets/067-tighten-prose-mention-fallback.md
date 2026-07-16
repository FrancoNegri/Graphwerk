# 067. Tighten the prose-mention fallback

Status: ready
Decision: docs/decisions/025-rationale-mention-confidence.md

## Goal

For files with no dedicated guidance bullet (ticket 066), the existing
prose mention-scanning (`attribute_files`/`attribute_symbols`) is the
fallback. Raise its precision on two confirmed false-positive patterns
without breaking genuine exact-filename mentions.

## Acceptance criteria

- A match via the bare-stem alternative (e.g. `webhook`) immediately
  followed by `.<identifier>` (e.g. `webhook.get_business`) is excluded —
  it denotes a symbol referenced *through* the file, not narration about
  it.
- A match via the full-filename or full-path alternative (e.g.
  `webhook.py`, `src/agendabot/webhook.py`) is **never** excluded by the
  above rule, even though it also has the shape "letters, dot, letters" —
  it's the file's own literal name. (This is the mistake an earlier draft
  of this fix made — a regression test must cover it directly.)
- A mention only counts if it sits inside a backtick-quoted code span
  (`` `...` ``) in the segment text — plain-prose word collisions with a
  file's stem (e.g. "conversation" as an ordinary word, vs. a file named
  `conversation.py`) no longer match.
- Regression cases from the dogfood transcript: `` `business_cache._load_business` ``
  does not attribute to `business_cache.py`; `` `webhook.py` `` (bare,
  backtick-quoted, no trailing `.identifier`) still attributes to
  `webhook.py`; "the various conversation helpers" (unquoted) does not
  attribute to `conversation.py`.

## Likely files

- `graphwerk/rationale/attribution.py` — `_mention_pattern`,
  `_distinct_token_pattern`, or their replacements.
- `tests/rationale/test_attribution.py`.

## Out of scope

- The guidance bullet parser (ticket 066), which this fallback only
  applies behind.
- Confidence tracking (ticket 068).
