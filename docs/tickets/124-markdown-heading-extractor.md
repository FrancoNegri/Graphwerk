# 124. Markdown heading extractor

Status: done
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

A new extractor turns one `.md` file into a `FileIndex`, the same contract
`PythonAstExtractor` implements for `.py` files, so Markdown files can index
and diff through the existing symbol-graph pipeline with no new model
classes.

## Acceptance criteria

- `MarkdownExtractor.extract(file_path, rel_path) -> FileIndex` in
  `graphwerk/indexing/markdown.py`.
- Each heading of level 2 or deeper (`## ...`, `### ...`, etc.) becomes one
  `SymbolInfo` with `kind="heading"`, `qualname` = the heading text; a
  repeated heading text within the same file is deduplicated with a
  numeric suffix so `qualname`s stay unique per file (mirrors how class
  methods already get unique qualnames).
- A symbol's `source` is the heading line plus every line up to (not
  including) the next heading of equal-or-shallower level, or end of file.
- Level-1 (`# ...`) headings are not extracted as symbols — treated as the
  document title, not a section.
- A file with no headings produces a `FileIndex` with an empty `symbols`
  dict (not a parse error).
- Unreadable files (`OSError`/`UnicodeDecodeError`) set `parse_error`,
  matching `PythonAstExtractor`'s existing behavior — no new failure mode.
- Stdlib only: line-based scanning, no new backend dependency.

## Likely files

- `graphwerk/indexing/markdown.py` — new extractor.
- `tests/test_markdown_extractor.py` — new file: heading extraction,
  dedup, section boundaries, no-headings case, unreadable file case.

## Out of scope

- Wiring the extractor into the walk/index dispatch (ticket 125).
- Nested-heading hierarchy in `qualname` (e.g. "Context > Decision") — flat
  heading text only, for v1.
- Any non-Markdown format.
