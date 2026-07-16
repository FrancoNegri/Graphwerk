# 064. Exclude test-file edges from import layering

Status: ready
Decision: docs/decisions/023-import-adjacency-drops-noise-filtered-and-test-edges.md

## Goal

A file imported only by its own test suite (no production importer) is
still a root — layer 0 — instead of being demoted to layer 1 by an edge
that only exists because it's well-tested.

## Acceptance criteria

- A new `_is_test_path` (or similarly named) helper in `graphwerk/layout.py`
  identifies a test file by pytest's own discovery convention: a
  `tests`/`test`-named path segment, or a filename matching
  `test_*.py`/`*_test.py`.
- `_import_adjacency` drops any `imports` edge whose *source* is a test
  file before building `imported_files_of` (target-side test files, i.e.
  production code importing a test helper, are unchanged — no evidence
  that direction needs special-casing).
- New test mirroring the dogfood shape: `app.py` (production, imports
  nothing) and `tests/test_app.py` (imports `app.py`) both present as
  nodes. Assert `app.py == 0` (not demoted by the test import) and
  `tests/test_app.py == 0` (still a root itself, unchanged from today).
- A test confirming the path heuristic itself: both `tests/foo.py` (segment
  match, non-`test_`-prefixed filename) and `pkg/test_bar.py` (filename
  match, not under a `tests/` segment) are recognized.
- Existing `_import_adjacency`/`_layers_by_longest_path` tests in
  `tests/test_layout.py` still pass — none of the current fixtures use
  test-shaped paths, so none should change value.

## Likely files

- `graphwerk/layout.py` — new test-path helper, `_import_adjacency`.
- `tests/test_layout.py` — new test-edge-exclusion cases.

## Out of scope

- The noise-filtered-intermediate-file fix (ticket 063 — independent;
  either can land first).
- Config-designated entry points (ADR 022/023 — still no evidence needed).
- Any UI change — `static/app.js` already renders whatever layer number it
  receives (tickets 061/062).
