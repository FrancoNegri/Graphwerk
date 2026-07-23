# 195. Promote the ticket `Decision:` line to a typed `implements` edge

Status: ready
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

A ticket's relationship to its ADR renders as its own edge kind
(`implements`) instead of disappearing into the generic `references`
bucket — so the review surface can draw "the decision this ticket
implements" distinctly from an arbitrary inline mention.

## Acceptance criteria

- The existing `Decision: docs/decisions/NNN-....md` line (already parsed
  by `markdown.py`'s `_DECISION_LINE`, ADR 046/052) stops contributing to
  `FileIndex.references` and instead produces a distinct signal — e.g. a
  new `FileIndex.decision_ref: str | None` field — that `GraphService`
  turns into `GraphEdge(source=<ticket id>, target=<ADR id>, kind=
  "implements")`.
- Every other `references`-producing source (inline `[text](path.md)`
  links) is unaffected — only the `Decision:` line's contribution changes
  kind.
- A test confirms a ticket's ADR no longer appears in its `references`
  edges but does appear as an `implements` edge; a ticket with a plain
  inline link to some other doc still gets a `references` edge for that
  link.

## Likely files

- `graphwerk/models.py` — new `FileIndex.decision_ref` field (or
  equivalent).
- `graphwerk/indexing/markdown.py` — stop merging the `Decision:` line
  into `references`; expose it separately.
- `graphwerk/service.py` — wire the new `implements` edge.
- `tests/` — updated/new cases per the acceptance criteria.

## Out of scope

- The code → ticket `implements` hop — ticket 196.
- Any change to how tickets write the `Decision:` line itself.
