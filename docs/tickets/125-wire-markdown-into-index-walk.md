# 125. Wire the Markdown extractor into the walk/index path

Status: done
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

`.md` files are enumerated alongside `.py` files and indexed with the
matching extractor (ticket 124), so a tree of Markdown docs diffs and
renders through the same pipeline a Python tree does — closing the
"invisible" gap ticket 009 flagged, scoped here to Markdown only.

## Acceptance criteria

- `graphwerk/indexing/walk.py` gains a way to enumerate `.md` files the
  same way `iter_python_files` enumerates `.py` files (git-aware, same
  symlink/ignore handling) — either a sibling `iter_markdown_files` or a
  generalized enumerator parameterized by extension; either way, no
  behavior change for existing `.py`-only trees.
- `ChangeSetBuilder._index_tree` (`graphwerk/staging/differ.py`) indexes
  both `.py` and `.md` files in one tree walk, dispatching to
  `PythonAstExtractor` or `MarkdownExtractor` by file extension.
- `GraphService.state_hash` (`graphwerk/service.py:152-159`) includes `.md`
  files in its fingerprint, so editing a doc's heading changes the polled
  hash the same way editing a function does.
- A tree containing only `.md` files (no `.py` at all) produces a non-empty
  graph — the scenario this decision exists for.
- A tree containing both kinds of files still diffs and renders both
  correctly (regression: existing Python-only behavior unchanged).

## Likely files

- `graphwerk/indexing/walk.py` — extension-aware enumeration.
- `graphwerk/staging/differ.py` — `ChangeSetBuilder` dispatches by
  extension.
- `graphwerk/service.py` — `state_hash` covers both extensions.
- `tests/test_differ.py`, `tests/test_service.py` — mixed-tree and
  Markdown-only cases.

## Out of scope

- Any other non-Markdown, non-Python file type (ticket 009's broader
  scope stays deferred).
- Cross-doc reference edges (ticket 126).
