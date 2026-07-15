# 022. Python token highlighting via stdlib tokenize

Status: ready
Decision: docs/decisions/007-sidebar-code-view.md

## Goal

A pure function classifies Python source into per-line highlight spans, so
the sidebar can color code without any client-side parsing or new backend
dependency.

## Acceptance criteria

- New module `graphwerk/highlight.py` exposing e.g.
  `highlight_lines(source) -> list[list[tuple[int, int, str]]]` — one span
  list per source line, spans as `(start_col, end_col, cls)`.
- Classes cover at least: `kw` (keywords), `def` (the name in
  `def`/`class` statements), `str` (strings incl. f-string parts), `com`
  (comments), `num` (numbers). Unclassified text gets no span.
- Multi-line strings produce spans on every line they cover.
- Input that `tokenize` rejects (syntax errors, binary junk) returns empty
  span lists for all lines — never raises (mid-edit saves are common,
  ticket 008).
- Unit tests cover: keywords/def names, single- and multi-line strings,
  f-strings, comments, numbers, syntax-error fallback, empty source.

## Likely files

- `graphwerk/highlight.py` — new (stdlib `tokenize`/`io` only)
- `tests/test_highlight.py` — new

## Out of scope

Non-Python classifiers (Phase 5); merging with diff ops (tickets 023/024);
any payload or UI change.
