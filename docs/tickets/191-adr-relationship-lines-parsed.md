# 191. Parse `Supersedes:`/`Amends:`/`Extends:` ADR front-matter lines

Status: ready
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

`MarkdownExtractor` recognizes the new three-line ADR relationship
convention and exposes it on `FileIndex` — the raw data the rest of ADR
065 wires into typed graph edges.

## Acceptance criteria

- `FileIndex` gains `adr_relationships: dict[str, set[str]]` — key is one
  of `"supersedes"` / `"amends"` / `"extends"`, value is the set of
  repo-root-relative target ADR paths.
- `MarkdownExtractor.extract()` scans for lines matching `^(Supersedes|
  Amends|Extends):\s*(.+)$` (case-sensitive, same convention style as the
  existing `Decision:` line), splits the value on commas, and resolves
  each bare ADR number (e.g. `037`) to its actual file by globbing
  `docs/decisions/037-*.md` relative to the repo root — same resolution
  approach `north-star`/`ticket` already use to find "the next number,"
  just in reverse (number → path instead of path → next number).
- A number with no matching file is skipped, not an error (an ADR renumber
  or typo shouldn't crash indexing) — but is asserted against in a test so
  a silent typo doesn't go unnoticed forever (e.g. logged or collected
  somewhere a later audit could check — exact mechanism is this ticket's
  call, doesn't need to be elaborate).
- Only applies to files under `docs/decisions/` — a `Supersedes:`-shaped
  line appearing in a ticket or any other Markdown file is ignored (this
  is an ADR-specific convention, not a generic Markdown feature).
- Existing `references` extraction (inline links, `Decision:` line) is
  unaffected — this is a pure addition alongside it.

## Likely files

- `graphwerk/models.py` — new `FileIndex.adr_relationships` field.
- `graphwerk/indexing/markdown.py` — the new parsing.
- `tests/` — cases for all three kinds, multi-target comma lists, and a
  non-ADR file with a coincidentally-matching line (should be ignored).

## Out of scope

- Wiring these into `GraphEdge`s — ticket 192.
- Backfilling real ADR files with the new lines — ticket 193.
