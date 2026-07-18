# 137. Multi-hop `via_imports` provenance for transitively-reached call edges

Status: done
Decision: docs/decisions/048-transitive-import-reachability-for-call-edges.md

## Goal

A `calls` edge whose reachability depends on a chain of re-exporting
imports (ticket 136) shows the reviewer *which* imports admit it — the
same "why do you believe this edge is real" evidence ADR 035/038 already
render for direct one-hop edges — instead of silently having no
explanation.

## Acceptance criteria

- For the ticket 136 fixture (`caller.py` → `pkg` → `pkg/inner.py::Thing`),
  `edge.via_imports` is a non-empty ordered sequence describing the full
  chain (at minimum: which module was imported at each hop and that
  hop's file), not `None`.
- The direct one-hop case (existing ADR 035/038 behavior) is unchanged —
  same `via_imports` shape and content as today for a target reached by a
  single import.
- Frontend calls panel (wherever `via_imports` is currently rendered per
  ADR 038/039) renders a multi-hop chain without crashing on the new
  shape; single-hop rendering is visually unchanged.

## Likely files

- `graphwerk/service.py` — `via_imports_entries`, building on the
  transitive traversal ticket 136 adds.
- `static/` — whatever component renders `via_imports` per ADR 038/039
  (calls panel / admitting-imports display).
- `tests/test_service.py` — multi-hop `via_imports` content assertions.

## Out of scope

- Ticket 136's core reachability fix — this ticket assumes it's already
  merged and only adds the explanation data/rendering on top.
- Any change to single-hop `via_imports` behavior.
