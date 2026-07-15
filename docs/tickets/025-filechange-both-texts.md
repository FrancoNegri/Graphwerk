# 025. FileChange carries base and staged full text

Status: done
Decision: docs/decisions/007-sidebar-code-view.md

## Goal

The change set exposes both sides' full file text, so the snapshot can
build file-level code views without re-reading files. Today `FileChange`
keeps a single `source` (staged, falling back to base).

## Acceptance criteria

- `FileChange` gains `base_source: str | None` and
  `staged_source: str | None`, populated by `ChangeSetBuilder.build` for
  every change (None for the missing side of added/deleted files and for
  unreadable files).
- The existing `source` attribute keeps its current staged-or-base
  semantics (consumers switch over in later tickets; nothing breaks now).
- File reads are not duplicated per file compared to today (the existing
  read paths are reorganized, not repeated).
- Unit tests cover: modified (both texts present and different), added
  (`base_source is None`), deleted (`staged_source is None`), unreadable
  file (both None, no exception).

## Likely files

- `graphwerk/staging/differ.py` — `FileChange` fields + builder plumbing
- `tests/test_differ.py` (or the existing differ test module) — extended

## Out of scope

Building or attaching code views (ticket 026); removing the legacy
`source` field (ticket 028); symbol-level texts (already available via
`FileIndex.symbols[...].source`).
