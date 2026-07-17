# 092. `GraphNode.is_test` in the snapshot payload

Status: done
Decision: docs/decisions/036-hide-tests-exempts-changed-and-affected.md

## Goal

The server, not the browser, decides which nodes are test code: every node
whose path matches the pytest discovery convention carries `is_test: true`
in the snapshot payload.

## Acceptance criteria

- `layout._is_test_path` is promoted to a public `is_test_path` (same
  module, same behavior; the private name's callers updated).
- `GraphNode` gains an `is_test` field; `to_dict()` includes it only when
  true (same omission style as other optional fields).
- `GraphService.snapshot()` sets it from the node's path for file *and*
  symbol nodes — a function inside `tests/test_foo.py` is flagged too.
- Unit tests: a snapshot over a tree containing `tests/test_x.py` and
  `pkg/mod.py` flags exactly the test file's nodes; `to_dict()` of an
  unflagged node has no `is_test` key.

## Likely files

- `graphwerk/layout.py` — rename `_is_test_path` → `is_test_path`
- `graphwerk/models.py` — field + serialization
- `graphwerk/service.py` — set the flag when building nodes
- `tests/test_service.py`, `tests/test_models.py` — coverage

## Out of scope

Any change to the JS filter (ticket 093). Any change to which edges the
layout excludes.
