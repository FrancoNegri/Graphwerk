# 129. `GraphNode.domain` field

Status: done
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

Every node in the snapshot payload carries a `domain` of `"doc"` or
`"code"`, so the frontend can filter the graph into a Design view and an
Implementation view (ticket 130) without guessing from file extension
client-side.

## Acceptance criteria

- `GraphNode.domain: str` (`"doc"` | `"code"`), added in
  `graphwerk/models.py`.
- File nodes get `domain="doc"` when the file was indexed by
  `MarkdownExtractor` (ticket 124/125), `domain="code"` otherwise.
- Every symbol/heading node inherits its parent file's `domain`.
- Existing snapshot consumers (tests, frontend) unaffected beyond the new
  field being present — no rendering change in this ticket.

## Likely files

- `graphwerk/models.py` — `GraphNode.domain` field + `to_dict`.
- `graphwerk/service.py` — set `domain` when building nodes, based on
  which extractor produced the file's `FileIndex`.
- `tests/test_service.py` — mixed doc/code tree snapshot has correct
  `domain` per node.

## Out of scope

- Frontend consumption (ticket 130).
- Any change to how the extractor dispatch itself works (ticket 125).
