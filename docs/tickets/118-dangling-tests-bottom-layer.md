# 118. Dangling test files sink to the bottom file layer

Status: done
Decision: docs/decisions/043-dangling-tests-bottom-layer.md

## Goal

Unpaired ("dangling") test files get a `layer` one past the deepest
ordinary file layer instead of landing at layer 0 alongside real entry
points.

## Acceptance criteria

- A dangling test file (`is_test_path` true, not a key in
  `pair_tests_with_files`'s result) gets
  `layer = max(layer of every non-test file node) + 1`.
- If there are no non-test file nodes at all, a dangling test file's layer
  is `0` (nothing to sink below).
- A dangling test file's `order` is still assigned via the existing
  barycenter/directory-grouping machinery, scoped to whatever else shares
  its new bottom layer, so multiple dangling tests stay grouped by
  directory rather than landing in arbitrary order.
- Paired test files are unaffected — still `layer = None`, per ADR
  041/ticket 111.
- Ordinary (non-test) file layers/orders are unaffected — this only
  touches nodes that were previously stranded at layer 0 with no
  adjacency.
- `tests/test_layout.py::test_import_from_test_file_does_not_demote_the_importee`
  updated: `tests/conftest.py` (unpaired) now asserts the bottom layer,
  not `0`.

## Likely files

- `graphwerk/layout.py` — `assign_layers`/`_import_adjacency` (or a small
  post-pass), compute and apply the bottom-layer override for dangling
  test nodes.
- `tests/test_layout.py` — update the existing dangling-test assertion;
  add coverage for multiple dangling tests sinking together and sharing
  directory-grouped order, and for the "no non-test files" edge case.

## Out of scope

- Paired-test placement — already shipped (tickets 110-112).
- Any frontend change — confirmed zero JS changes needed (layer-band
  rendering in `static/app.js` is already generic over layer count/value).
- Visual/styling treatment for the bottom band.
