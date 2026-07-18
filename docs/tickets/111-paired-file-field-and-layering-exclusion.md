# 111. `GraphNode.paired_file` payload field; paired tests excluded from file layering

Status: done
Decision: docs/decisions/041-paired-test-file-placement.md

## Goal

Wire ticket 110's pairing into the snapshot: paired test nodes carry the id
of their matched file in the payload, and drop out of the normal
import-depth file layering so they no longer occupy a layer-0 band slot.

## Acceptance criteria

- `GraphNode` gains `paired_file: str | None = None`; `to_dict` includes
  `paired_file` only when set (same conditional-inclusion convention as
  `is_test`).
- `assign_layers` (or its caller in `graphwerk/service.py`) calls
  `pair_tests_with_files` and sets `paired_file` on the matched test nodes.
- A paired test file's `layer` and `order` are `None` in the resulting
  nodes — it's excluded from `_import_adjacency`'s node set (or
  equivalently stripped of its layer/order after assignment), the same way
  its own import edges are already excluded (ADR 023).
- An unpaired test file's `layer`/`order` are unchanged from today's
  behavior (still assigned via the normal file-layer graph).
- A source file's own `layer`/`order`/`group` are unaffected by whether it
  has a paired test.

## Likely files

- `graphwerk/models.py` — `paired_file` field + conditional payload.
- `graphwerk/layout.py` — thread pairing into `assign_layers`, exclude
  paired test nodes from the file-layer graph.
- `graphwerk/service.py` — pass whatever `assign_layers` now needs (only if
  its call site changes).
- `tests/test_layout.py`, `tests/test_models.py`, `tests/test_service.py` —
  coverage for the exclusion and the payload field.

## Out of scope

- The pairing algorithm itself — ticket 110.
- Client-side positioning — ticket 112.
