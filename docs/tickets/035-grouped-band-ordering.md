# 035. Directory-grouped within-band ordering

Status: ready
Decision: docs/decisions/010-directory-band-grouping.md

## Goal

Files sharing a top-level directory sit contiguously within their band,
with group order inheriting the barycenter result — bands read as labeled
runs instead of interleaved src/tests chips.

## Acceptance criteria

- After the barycenter sweeps, each *file* band's order is re-sorted:
  groups (top-level directory of the node's path; repo-root files form
  their own group) ordered by mean barycenter position of members, members
  keeping barycenter order within the group. `GraphNode.order` reflects
  the final order.
- Symbol (function) bands are untouched by grouping (pytest asserts an
  intra-file ordering is identical with and without mixed paths).
- Deterministic: same input → same order (existing stability tests keep
  passing).
- A pytest case with two groups interleaved by barycenter shows contiguous
  groups afterward, group order following mean position.

## Likely files

- `graphwerk/layout.py` — grouping pass after `_orders_by_barycenter`
- `tests/` — grouping cases

## Out of scope

- The `group` payload field (ticket 036) and any UI change (ticket 037).
- Grouping below the top-level directory.
