# 021. Symbol-level mention attribution

Status: done
Decision: docs/decisions/006-rationale-mining-v2.md

Depends on: tickets 018-020.

## Goal

Symbol nodes get their own rationale when the transcript names the symbol,
under the `rel::qualname` key shape the sidecar already uses. The service
already calls `why_for(rel, qualname)` per symbol node, so this is purely a
mining/lookup change.

## Acceptance criteria

- Attribution produces `rel::qualname` entries for changed symbols whose
  final qualname component appears as a distinct token in a segment;
  latest mention wins, same token rules as ticket 019.
- If the same symbol name is edited in more than one file, a segment only
  counts for the file it also mentions; ambiguous mentions attribute to
  neither.
- `why_for(rel, qualname)` prefers, in order: sidecar `rel::qualname`,
  sidecar `rel`, transcript `rel::qualname`, transcript `rel`.
- Unit tests cover: symbol mention beating the file-level why for that
  node while siblings keep the file-level why; ambiguous same-name
  symbols across two files; `why_for` precedence order.

## Likely files

- `graphwerk/rationale/attribution.py` — symbol attribution
- `graphwerk/rationale/miner.py` — store symbol entries; `why_for` lookup
  order
- `tests/test_attribution.py`, `tests/test_rationale.py` — extended

## Out of scope

Changing what counts as a changed symbol (differ territory); UI changes —
the sidebar already renders whatever `why` the payload carries.
