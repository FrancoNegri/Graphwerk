# 056. Cache per-node code view by content identity

Status: done
Decision: docs/decisions/019-snapshot-recompute-caching.md

## Goal

An unchanged node's syntax-highlighted code view (`_code_view` →
`build_code_view` → `highlight_lines`) is computed once per distinct
`(base_text, staged_text)` pair, not recomputed on every `snapshot()` call —
so the 81%-`UNCHANGED` majority of nodes stop paying full tokenize/diff cost
on every poll-triggered rebuild.

## Acceptance criteria

- Calling `GraphService.snapshot()` twice in a row with no filesystem
  changes computes each distinct node's code view exactly once total
  across both calls (test via a call-count spy on `highlight_lines` or
  `build_code_view`), not once per `snapshot()` call.
- A node whose base/staged text changes between calls gets its code view
  recomputed on the next call; a node whose text is unchanged does not.
- Existing sidebar/code-view tests (merged line view, highlight spans,
  diff overlay) pass unchanged.

## Likely files

- `graphwerk/service.py` — `_code_view` (or a small wrapping cache owned by
  `GraphService`) memoizes by the identity/hash of its two text inputs.
- `graphwerk/codeview.py` — no contract change expected; cache lives above
  it in `service.py` unless a natural seam appears during TDD.

## Out of scope

- Caching the AST/index layer (that's ticket 055).
- Moving code-view computation to an on-demand endpoint instead of the
  inline snapshot payload — deferred per ADR 019 (contract change, not
  needed if caching alone closes the gap).
