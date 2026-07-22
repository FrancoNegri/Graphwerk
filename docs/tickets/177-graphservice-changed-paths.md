# 177. `GraphService.changed_paths()`

Status: done
Decision: docs/decisions/061-whole-tree-commit-all-revert-all.md

## Goal

Give callers the rel paths a pair's current diff reports as changed, so
commit-all/revert-all (ticket 178) know what to scope to without
re-deriving diff logic themselves.

## Acceptance criteria

- `GraphService.changed_paths() -> list[str]` in `graphwerk/service.py`
  returns the rel paths of `self.builder.build()` entries whose `status`
  is in the module's existing `CHANGED` set (`MODIFIED`/`ADDED`/
  `DELETED`) — the same set `snapshot()` already uses to decide
  `why`/color, so this reuses that definition rather than inventing a
  second one.
- A test builds a `GraphService` against a small temp git repo where one
  file is modified, one is newly added, and one is left unchanged, and
  asserts `changed_paths()` returns exactly the modified and added rel
  paths, not the unchanged one.

## Likely files

- `graphwerk/service.py` — the new method.
- `tests/test_service.py` — the test above.

## Out of scope

- Any endpoint wiring (ticket 178) or git mutation (ticket 176) — this
  ticket only exposes the path list.
