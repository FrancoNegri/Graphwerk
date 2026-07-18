# 126. Cross-doc reference edges

Status: done
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

Relative Markdown links between tracked docs (an ADR linking its tickets,
a ticket linking its `Decision:` ADR) become graph edges, the same way
imports become `imports`-kind edges — this is what makes the knowledge
base render as *a graph* rather than a flat set of file boxes.

## Acceptance criteria

- A new `GraphEdge.kind == "references"`, added the same way
  `_add_import_edges` adds `"imports"` edges (`graphwerk/service.py`).
- For each `.md` `FileIndex`, in-repo relative Markdown links
  (`[text](relative/path.md)` or `relative/path.md#anchor`) resolve to a
  target file node when that path exists in the same tree; unresolvable
  links (external URLs, paths outside the tree) are silently skipped —
  same "never a new failure mode" posture as import resolution.
- The `Decision: docs/decisions/NNN-....md` line already used in every
  ticket file is recognized as a reference too, not just inline
  `[text](path)` links.
- A `references` edge carries `status` computed the same way `imports`
  edges do (unchanged/added/removed based on whether the link exists in
  base vs. staged).
- Existing `calls`/`imports` edges and their rendering are unaffected.

## Likely files

- `graphwerk/indexing/markdown.py` — link extraction alongside heading
  extraction (ticket 124), likely a new `FileIndex` field analogous to
  `imports`/`import_statements`.
- `graphwerk/service.py` — `_add_reference_edges`, called alongside
  `_add_import_edges`.
- `graphwerk/models.py` — `"references"` added to `GraphEdge.kind`'s
  allowed values (comment/type only, it's already a free string).
- `tests/test_service.py` — an ADR-links-ticket fixture produces a
  `references` edge.

## Out of scope

- Semantic/inferred relationships beyond explicit links (ADR 046,
  Alternatives).
- Edge coloring/click-panel treatment beyond reusing the existing
  `imports`-edge rendering path — new UI chrome only if the reused path
  doesn't already cover it.
