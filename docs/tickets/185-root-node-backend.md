# 185. Backend: synthesize the `Root` entry-point node

Status: done
Decision: docs/decisions/063-root-entry-point-node.md

## Goal

`GraphService.snapshot()` adds one synthetic `Root` node and one
`entrypoint`-kind edge to every code-domain file node currently at
`layer == 0`, after `assign_layers()` has run.

## Acceptance criteria

- After `assign_layers(snap.nodes, snap.edges)` runs inside `snapshot()`,
  a new step adds `GraphNode(id="__root__", kind="root", label="Root",
  path="", domain="code", layer=-1, order=0)` to `snap.nodes`, plus one
  `GraphEdge(source="__root__", target=<id>, kind="entrypoint")` per
  `file`-kind, `domain == "code"` node with `layer == 0`.
- `Root` is only added when at least one code-domain file node exists at
  layer 0 (an empty/all-doc snapshot adds no `Root`).
- `Root` and its edges are never included in `changed_paths()` or any
  diff-scoped computation — confirm by inspecting `changed_paths()`
  doesn't need modification (it's built from `self.builder.build()`,
  independent of the node list `Root` is added to).
- `Root`'s node carries no status/diff/why/code/source (all default/None)
  — verify `to_dict()` serializes it without error.
- New test(s) in the `GraphService` snapshot test suite: a small repo with
  two independent entry-point files produces exactly one `Root` node with
  edges to both; a repo with no Python files (doc-only) produces no `Root`
  node.

## Likely files

- `graphwerk/service.py` — new step in `snapshot()`, e.g.
  `self._add_root_node(snap)`, called after `assign_layers`.
- `tests/test_service.py` (or wherever `GraphService.snapshot()` is
  tested) — new test cases.

## Out of scope

- Frontend rendering — ticket 186.
- Any doc-domain equivalent — explicitly out of scope per ADR 063.
