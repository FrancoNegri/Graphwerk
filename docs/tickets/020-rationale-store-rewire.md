# 020. RationaleStore mines via parser + attribution

Status: ready
Decision: docs/decisions/006-rationale-mining-v2.md

## Goal

`RationaleStore` produces its transcript rationale through the new parser
(ticket 018) and file attribution (ticket 019), with the old
preceding-edit narration kept as fallback for unmentioned files. The
dogfood transcript shape (one lead-in, batched edits, rich final summary)
now yields distinct per-file whys.

## Acceptance criteria

- `_mine_transcript` builds on `parse_transcript` + `attribute_files`:
  mention-attributed text wins; files with edits but no mention fall back
  to the last segment before their edit (current behavior); sidecar
  precedence in `why_for` is unchanged.
- `why_for` signature and the service layer are untouched.
- A regression test encodes the dogfood shape: one short lead-in, several
  edits, then a bullet summary naming each file — each file gets its own
  summary line, not the shared lead-in.
- A fallback test: an edited file never mentioned in any text still gets
  the preceding narration.
- Existing rationale tests keep passing (adjusted only if they asserted
  the old single-block behavior as such).

## Likely files

- `graphwerk/rationale/miner.py` — `_mine_transcript` rewired; parsing
  code moved out or deleted
- `tests/test_rationale.py` (or equivalent existing test module) — updated
  plus regression test

## Out of scope

Symbol-level (`rel::qualname`) transcript entries — ticket 021.
