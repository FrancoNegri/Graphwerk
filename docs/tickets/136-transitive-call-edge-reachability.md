# 136. Transitive import reachability for call-edge resolution

Status: ready
Decision: docs/decisions/048-transitive-import-reachability-for-call-edges.md

## Goal

A caller's `calls` edge can resolve to a target reached through a chain of
resolvable imports (e.g. `cli.py` imports `pkg`, `pkg/__init__.py`
re-exports `Name` from `pkg/inner.py`), not just a direct one-hop import —
so real cross-module calls through a re-exporting package no longer get
silently dropped by ADR 034's reachability filter.

## Acceptance criteria

- Fixture reproducing the dogfood shape: a package `pkg/__init__.py`
  containing only `from pkg.inner import Thing`, a `pkg/inner.py`
  defining `class Thing`, and a third file `caller.py` doing
  `from pkg import Thing` and calling `Thing()`. `GraphService.snapshot()`
  produces a `calls` edge from `caller.py`'s calling symbol to
  `pkg/inner.py::Thing`.
- A chain of three or more re-exporting hops (e.g. `outer/__init__.py` →
  `outer/mid/__init__.py` → `outer/mid/inner.py`) still resolves — the
  traversal isn't hardcoded to exactly one extra hop.
- Existing ADR 032/034 protections still hold on the new traversal:
  - A caller still cannot resolve to a same-named symbol in a file that is
    not transitively reachable from it (extend
    `test_caller_does_not_resolve_to_same_named_symbol_in_a_file_it_does_not_import`-style
    coverage with an unreachable file at the end of an otherwise-unrelated
    chain).
  - Tree membership (base vs. staged) is respected at every hop, not just
    the first — a deleted caller's chain resolves only through base-tree
    files, a non-deleted caller's only through staged-tree files.
  - A cyclic import graph (two files each importing the other) does not
    hang or crash the traversal.
- `via_imports_entries` no longer assumes every reachable `target_rel` is
  a direct one-hop import: it returns `None` (no admitting-import
  explanation) for a call edge whose only path is multi-hop, instead of
  raising `KeyError`. Covered by a test asserting `edge.via_imports is
  None` for the multi-hop fixture above.
- All existing tests in `tests/test_service.py` (ADR 032/034/035/038
  coverage) still pass unmodified.

## Likely files

- `graphwerk/service.py` — `GraphService._add_call_edges`,
  `admitting_modules_by_file`, `via_imports_entries`: replace the one-hop
  `modules_by_file` used for the `allowed_files` reachability check with a
  memoized, cycle-guarded transitive closure; keep `modules_by_file` (or
  equivalent one-hop data) around for the `via_imports` lookup and guard
  it against multi-hop targets.
- `tests/test_service.py` — new fixtures/tests per the acceptance criteria
  above, alongside the existing ADR 034 tests
  (`test_caller_resolves_to_same_named_symbol_in_a_file_it_does_import`
  and neighbors, around line 464-529).

## Out of scope

- Multi-hop `via_imports` provenance (explaining *which* chain of imports
  admits a transitively-reached edge) — ticket 137.
- Relative-import dot-level resolution — ticket 054, unrelated.
- Any change to `PythonAstExtractor`, `FileIndex`, or `SymbolInfo`.
