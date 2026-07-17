# 032. Call-edge resolution only matches targets that share a tree with the caller

Status: accepted
Date: 2026-07-17

## Context

Phase 2 goal (docs/04-roadmap.md): "real-repo hardening — fix what the
differ/indexer trips on." Dogfooding against agendabot's `webhook.py` →
`business.py` extraction (the same session that drove ADR 029) surfaced a
second, separate issue on `calls` edges rather than node coloring.

`GraphService._add_call_edges` (`graphwerk/service.py`) resolves each
caller's called (simple, unqualified) names against **every node in the
snapshot sharing that name**, with no regard for which of the two parsed
trees (base vs. staged) either the caller or the candidate target actually
belongs to. In steady state this is harmless — a name collision across
unrelated files is rare and, when it happens, both nodes are usually
`unchanged` so the edge is uninteresting. It stops being harmless the
moment a symbol relocates to a new file (a common AI-refactor shape): the
old copy becomes a `deleted` node in the old file, the new copy becomes an
`added` node in the new file, and both share the same simple name.

Traced with the real dogfood data (`/api/graph` against
`agendabot`/`agendabot-graphwerk-staging`, `_load_business` and its
siblings moved from `webhook.py` to `business.py`):

- Edge status is purely borrowed from the target node's status
  (`_mark_edge_status`, ADR 016) — an edge means "this call points at
  something with this status," not "this specific call relationship was
  added/removed."
- Each caller's `calls` set is sourced from exactly one tree already:
  `info = staged_info or base_info` (service.py) — a `deleted` node's
  calls always come from `base_info` (it has no `staged_info`); every
  other status's calls come from `staged_info`.
- Because target lookup (`name_to_ids.get(name, [])`) ignores tree
  membership, a `deleted` caller (base-tree-only, e.g.
  `webhook.py::_load_business`) also resolves to `added` targets that only
  exist in the staged tree (e.g. `business.py::_config_hash`), and vice
  versa. These two nodes never coexisted in either parsed tree — the edge
  represents no real call site in any single version of the code. This is
  a **phantom edge**, distinct from the (correct) `deleted → deleted`
  edges that reconstruct the old file's real internal wiring as it stood
  in base.

## Decision

Filter target candidates in `_add_call_edges` so a caller only resolves to
targets that share its calls-list's tree of origin:

- A caller whose calls came from `base_info` (i.e. status `deleted`) may
  only resolve to targets that exist in base: status `deleted`,
  `modified`, or `unchanged` — never `added`.
- A caller whose calls came from `staged_info` (status `added`,
  `modified`, or `unchanged`) may only resolve to targets that exist in
  staged: status `added`, `modified`, or `unchanged` — never `deleted`.

Equivalently, the only two forbidden pairings are (`deleted` caller →
`added` target) and (non-`deleted` caller → `deleted` target). No new
field on `GraphNode`/`GraphEdge` is needed — the filter reads the
`Status` already computed for both endpoints.

## Alternatives considered

- **Move detection** (reunify a deleted+added pair as "the same symbol,
  relocated," via a body-similarity heuristic or similar) — would also let
  the graph draw an explicit "moved to" relationship instead of
  delete+add. Rejected for now: meaningfully bigger (similarity
  threshold, false-positive risk, likely a new status/field on the
  language-neutral `SymbolInfo` contract), and risks drifting toward
  hunk-to-symbol mapping, which CLAUDE.md's differ invariant explicitly
  rules out for the *status* differ. ADR 029 already deferred this once
  under "symbol-move detection"; re-affirmed here rather than re-opened.
  Worth its own `north-star` pass later if move-shaped refactors keep
  showing up as disruptive during dogfooding.
- **Do nothing, document the behavior** — zero cost, but leaves a genuinely
  misleading edge (two nodes that never coexisted in any single tree,
  wired together) in the review surface, undermining the "structural
  context" the graph exists to provide (docs/02).

## Consequences

- Phantom cross-tree call edges (e.g. `deleted` → `added` between a
  relocated symbol's old and new copies) stop appearing.
- The `deleted → deleted` edges that reconstruct a gutted file's former
  internal wiring are unaffected — confirmed during dogfooding that this
  reading is correct and useful as-is.
- `_mark_affected`'s "unchanged symbol calls into changed code" signal
  gets slightly more precise as a side effect: an `unchanged` node can no
  longer appear to call a `deleted` target it never actually called in the
  staged tree.
- Pure backend change, one function, no new dependency, no model change —
  consistent with all standing invariants.

## Out of scope

- Symbol-move detection / reunifying relocated symbols' identity — stays
  deferred (see Alternatives).
- Tracking more than one calls-list per node (e.g. a `modified` node's
  pre-edit calls, from `base_info`, are still not tracked at all) — a
  separate, pre-existing simplification, not touched here.
