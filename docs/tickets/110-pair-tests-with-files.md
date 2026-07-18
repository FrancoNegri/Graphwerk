# 110. `pair_tests_with_files`: mirror-key matching between test and source files

Status: done
Decision: docs/decisions/041-paired-test-file-placement.md

## Goal

A pure, pytest-covered function in `graphwerk/layout.py` that matches each
test file to the one source file it mirrors by path convention, with no
guessing on ambiguous or unmatched cases.

## Acceptance criteria

- Given a list of file-kind `GraphNode`s, `pair_tests_with_files` returns a
  `dict[str, str]` mapping each paired test file's node id to its matched
  source file's node id.
- Mirror key: a file's path with its top-level directory dropped; for test
  files, additionally drop a leading `tests`/`test` path segment and a
  `test_`/`_test` filename affix (reuse `is_test_path`'s segment/affix
  convention from the same module rather than re-deriving it).
- `tests/test_layout.py` pairs with `graphwerk/layout.py`;
  `tests/indexing/test_python_ast.py` pairs with
  `graphwerk/indexing/python_ast.py` (directory-mirrored case).
- A test file whose mirror key matches zero source files, or more than one,
  is omitted from the returned mapping (no arbitrary tie-break) —
  e.g. a lone `tests/conftest.py` with no `graphwerk/conftest.py`.
- Non-test files never appear as keys in the returned mapping.

## Likely files

- `graphwerk/layout.py` — add `pair_tests_with_files`.
- `tests/test_layout.py` — coverage for matched, directory-mirrored,
  ambiguous, and unmatched cases.

## Out of scope

- Wiring the result into `assign_layers`, the payload, or excluding paired
  tests from the file-layer graph — ticket 111.
- Any client-side change — ticket 112.
