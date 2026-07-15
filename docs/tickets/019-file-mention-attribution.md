# 019. File-level mention attribution

Status: done
Decision: docs/decisions/006-rationale-mining-v2.md

## Goal

Given ordered transcript segments and the set of edited files, pick each
file's rationale: the latest segment that mentions the file. This is the
piece that fixes the dogfood failure — wrap-up summaries win over the weak
lead-in sentence.

## Acceptance criteria

- New pure function (e.g. `attribute_files(segments, rel_paths)` in
  `graphwerk/rationale/attribution.py`) returning `rel_path -> segment
  text`, truncated to the existing `MAX_WHY_LEN`.
- A segment "mentions" a file when its relative path, basename
  (`miner.py`), or stem (`miner`) appears as a distinct token — matches
  inside backticks and adjacent punctuation count; substrings of longer
  identifiers do not (`miner` must not match `determiner`).
- When several segments mention a file, the latest one (highest index)
  wins.
- Files mentioned nowhere are absent from the result (fallback is ticket
  020's concern).
- Unit tests cover: bullet summary attributing different files to
  different lines, later mention overriding earlier, stem vs. substring
  discrimination, unmentioned file.

## Likely files

- `graphwerk/rationale/attribution.py` — new (pure, stdlib-only)
- `tests/test_attribution.py` — new

## Out of scope

Symbol-level attribution (ticket 021); wiring into `RationaleStore`
(ticket 020).
