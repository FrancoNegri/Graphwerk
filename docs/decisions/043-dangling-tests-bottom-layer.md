# 043. Dangling test files sink to the bottom layer, not layer 0

Status: proposed
Date: 2026-07-17

## Context

ADR 041 paired tests to their source file by mirror-key convention and
anchored paired pills directly below their file — but Decision point 2
explicitly kept unpaired ("dangling") tests unchanged: "stays exactly where
it renders today (its own root-layer slot)." That slot is layer 0 — the
same band as genuine entry points (ADR 022: layer 0 = files nothing
imports). Dangling tests land there not because they're roots but because
their own import edges are already excluded from the file graph (ADR
023/ticket 064) while — unlike paired tests — they're still counted as
*nodes* in that graph (`graphwerk/layout.py:141-142`), so they have zero
adjacency and settle at layer 0 by default, indistinguishable from real
entry points. `tests/test_layout.py::test_import_from_test_file_does_not_demote_the_importee`
documents exactly this today (`layers["tests/conftest.py"] == 0`).

This is the exact complaint driving this decision: "dangling tests should
appear at the bottom of the tree (currently appearing in the first
layer)." Same Phase 2 Scale UX line as ADR 041 (docs/04-roadmap.md), same
product-concept structural-context promise (docs/02) — a test the pairing
convention can't resolve should still read as peripheral, not
architecturally central.

## Decision

Dangling test files (`is_test_path` true, absent from
`pair_tests_with_files`'s result) get pushed to one layer below the
deepest layer among ordinary (non-test) file nodes — the bottom of the
rendered tree, since layer 0 renders at the top (ADR 022/ticket 062) and
layer numbers increase downward. Concretely, in `graphwerk/layout.py`:

- Compute the normal file-import layering exactly as today for
  non-dangling file nodes.
- Assign every dangling test file `layer = max(other file layers) + 1`
  (or `0` if there are no other file nodes to sink below).
- Existing ordering machinery (barycenter sweep + directory grouping, ADR
  008/010) still runs over whatever nodes share that bottom layer, so
  multiple dangling tests stay tidily grouped by directory instead of
  landing in arbitrary order.
- Paired tests are unaffected — still fully excluded from file layering
  (`layer = None`) and positioned by ADR 041's client-side anchor.
- No frontend change: confirmed the layer-band renderer (`static/app.js`)
  treats `layer` as a dynamically-sorted Map key with no assumption about
  the maximum value or count of layers (layers are sorted ascending and
  chained with a fixed gap, not indexed into a fixed-size structure), so a
  new deepest layer flows through the exact same generic path with zero JS
  changes — consistent with ADR 005 (JS stays thin, layout logic is
  Python).

## Alternatives considered

- **Exclude dangling tests from the file graph entirely (like paired
  tests) and give them a client-side "pin to graph bottom" position
  pass** — rejected: paired tests anchor to one specific node (their
  file's rendered position); dangling tests have no such anchor, so this
  would need a new "bottom of the whole graph" concept in the frontend
  that doesn't exist today, pushing layout logic into JS where ADR 005
  says it shouldn't live. The server-side layer-number approach reuses
  machinery that already exists and needs no new payload field or JS code.
- **Leave dangling tests at layer 0 but visually de-emphasize them
  (dim/fade)** — rejected: doesn't fix the actual complaint — they'd still
  occupy the entry-point band, crowding it and misrepresenting structure.
  This repurposes styling to paper over a layout problem instead of fixing
  the layout.

## Consequences

- Dangling tests read as peripheral (bottom of the graph) instead of
  competing with real entry points for the top band.
- Layer 0 (and every layer below it) regains its meaning as strictly
  import-depth-derived, since a special-cased category of node no longer
  contaminates it by lacking adjacency.
- One existing test
  (`test_import_from_test_file_does_not_demote_the_importee`) needs its
  dangling-test-layer assertion updated to the new bottom-layer
  expectation — an intentional behavior change, not a regression.
- No architecture invariant touched: still Python/stdlib layout logic
  (`graphwerk/layout.py`), still consumed generically by the existing thin
  JS renderer.

## Out of scope

- Any visual distinction (tint, label, connector) marking the bottom band
  as "dangling tests" specifically — not requested; they render exactly
  like any other bottom-layer file.
- Collision/overlap avoidance within the bottom band — same open item ADR
  041 already deferred, unaffected by this change.
- Revisiting the pairing convention itself (ADR 041's mirror-key
  matching) — this only changes where *unpaired* results land.
