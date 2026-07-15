# 023. Merged line view of base vs staged text

Status: ready
Decision: docs/decisions/007-sidebar-code-view.md

## Goal

A pure function turns one node's base and staged text into the full
ordered line list with per-line diff ops — the entire source with removed
lines interleaved where they were, instead of isolated hunks.

## Acceptance criteria

- New module `graphwerk/codeview.py` exposing e.g.
  `merge_lines(base_text, staged_text) -> list[CodeLine]` where each line
  carries: text, op (`ctx` | `add` | `del`), and the 1-based line number
  on its originating side (staged for `ctx`/`add`, base for `del`).
- Built on `difflib.SequenceMatcher` opcodes; `replace` blocks emit the
  `del` lines then the `add` lines.
- Degenerate cases: identical texts → all `ctx`; `base_text` None/empty →
  all `add`; `staged_text` None/empty → all `del`; both empty → empty
  list.
- Unit tests cover: a mid-file modification (dels interleaved at the right
  spot), pure insertion, pure deletion, replace block ordering, the
  degenerate cases, and origin line numbers on both sides.

## Likely files

- `graphwerk/codeview.py` — new (stdlib `difflib` only)
- `tests/test_codeview.py` — new

## Out of scope

Highlight spans (ticket 024); word-level intra-line diffing (ADR 007 out
of scope); anything touching differ/service.
