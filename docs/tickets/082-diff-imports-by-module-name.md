# 082. Diff imports as added/removed/unchanged per file

Status: done
Decision: docs/decisions/033-import-edge-status-and-pertinent-import-inspection.md

## Goal

`ChangeSetBuilder.build()` computes a per-module import status for each
file, the same way it already computes a per-symbol status — so later
tickets can put a real `Status` on import edges instead of the current
hardcoded `Status.UNCHANGED`.

## Acceptance criteria

- `FileChange` gains `imports: dict[str, Status]` (module name -> status),
  populated in `ChangeSetBuilder.build()` alongside the existing
  `change.symbols` population, for every branch (`ADDED`, `DELETED`,
  `UNCHANGED`, `MODIFIED` file).
- For a `MODIFIED` file: a module in both `base.imports` and
  `staged.imports` -> `Status.UNCHANGED`; staged-only -> `Status.ADDED`;
  base-only -> `Status.DELETED`. Computed over the union
  `base.imports | staged.imports`, mirroring the existing
  `set(base.symbols) | set(staged.symbols)` union used for symbols.
- For an `ADDED` file: every module in `staged.imports` -> `Status.ADDED`.
- For a `DELETED` file: every module in `base.imports` -> `Status.DELETED`.
- For an `UNCHANGED` file: every module in `staged.imports` ->
  `Status.UNCHANGED`.
- Test: a modified file that adds one import and removes another (keeping a
  third unchanged) produces the expected three-way split in
  `change.imports`.
- Test: an added file's `change.imports` are all `Status.ADDED`; a deleted
  file's are all `Status.DELETED`.

## Likely files

- `graphwerk/staging/differ.py` — `FileChange.__init__` (new `imports`
  dict) and `ChangeSetBuilder.build()` (populate it per branch).
- `tests/` (wherever `ChangeSetBuilder`/`FileChange` is currently covered)
  — new cases per acceptance criteria above.

## Out of scope

- Anything on `GraphEdge`/`GraphService` — this ticket only produces the
  per-file `imports` status map; wiring it onto edges is ticket 083.
- Line-level import text (ADR 033, "Alternatives considered").
