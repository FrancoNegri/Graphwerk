# 081. Scope call-edge target resolution to the caller's tree

Status: done
Decision: docs/decisions/032-call-edge-resolution-scoped-to-shared-tree.md

## Goal

`GraphService._add_call_edges` stops creating call edges between a caller
and a target that never coexisted in the same parsed tree (base or
staged) — killing phantom edges like a `deleted` symbol appearing to call
an `added` symbol it never actually called.

## Acceptance criteria

- In `_add_call_edges` (`graphwerk/service.py`), a caller whose calls came
  from `base_info` (status `deleted`) only produces edges to targets with
  status `deleted`, `modified`, or `unchanged` — never `added`.
- A caller whose calls came from `staged_info` (status `added`,
  `modified`, or `unchanged`) only produces edges to targets with status
  `added`, `modified`, or `unchanged` — never `deleted`.
- Existing behavior is unchanged for same-tree cases: a `deleted` caller
  still resolves to a `deleted` target it actually called in base (the
  "old file's internal wiring" case, confirmed correct during dogfooding);
  an `added`/`modified`/`unchanged` caller still resolves normally to
  other staged-tree targets.
- Test: two symbols with the same simple name, one `deleted` (base-only)
  and one `added` (staged-only), where the `deleted` one's call list
  includes a name matching another `added`-only symbol — asserts no edge
  is created between them.
- Test: a `deleted` caller whose call list matches another `deleted`
  symbol still produces that edge (regression guard for the case ADR 032
  explicitly keeps).
- Test: an `unchanged`/`modified` caller whose call list matches a
  `deleted` symbol produces no edge (the mirror phantom case).

## Likely files

- `graphwerk/service.py` — `_add_call_edges`: filter target candidates by
  shared tree membership, derived from each node's existing `Status`.
- `tests/` (wherever `GraphService`/`_add_call_edges` is currently
  covered) — new cases per acceptance criteria above.

## Out of scope

- Symbol-move detection / reunifying a relocated symbol's old and new
  identity (ADR 032, "Alternatives considered").
- Tracking a second (pre-edit) calls list for `modified` nodes.
