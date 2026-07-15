# 018. Transcript parser: ordered segments + edit events

Status: done
Decision: docs/decisions/006-rationale-mining-v2.md

## Goal

A single pure parser turns a session transcript (JSONL) into the two things
attribution needs: an ordered list of assistant text segments, and the edit
events with their position in that order. Today parsing is tangled into
`RationaleStore._mine_transcript` and keeps only one text block.

## Acceptance criteria

- New module `graphwerk/rationale/transcript.py` exposing a function (e.g.
  `parse_transcript(path, staged_root)`) that returns ordered segments and
  edit events.
- Assistant `text` blocks are split into segments on blank lines, and
  bullet/list lines (`- `, `* `, `1. `) each become their own segment;
  segments preserve transcript order via an index.
- Edit events carry the staged-relative path (same resolution rules as the
  current `_to_rel`) and the index of the last segment seen before the edit.
- Tool calls in `EDIT_TOOLS` are recognized; other tools and non-assistant
  entries are ignored; malformed JSONL lines and paths outside the staged
  root are skipped without error.
- Unit tests cover: multi-paragraph text block, bullet-list summary block,
  edits interleaved with narration, malformed lines, out-of-root paths.

## Likely files

- `graphwerk/rationale/transcript.py` — new parser (pure, stdlib-only)
- `tests/test_transcript.py` — new

## Out of scope

Attribution logic (ticket 019) and any change to `RationaleStore` — the
miner still uses its old path until ticket 020 rewires it.
