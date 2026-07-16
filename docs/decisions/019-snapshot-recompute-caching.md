# 019. Cache repeated snapshot recomputation (indexing + code view)

Status: accepted
Date: 2026-07-16

## Context

Phase 2's exit criterion (docs/04-roadmap.md) is dogfooding a real Claude Code
session end to end. Profiling `GraphService.snapshot()` directly against a
real dogfood pair (`agendabot` base / `agendabot-graphwerk-staging`, 117-121
Python files — see [[project_agendabot_dogfood]]) shows it takes ~2.7-5.5s
per call. cProfile breakdown:

- ~2.5s in `ChangeSetBuilder.build()` (`graphwerk/staging/differ.py`), almost
  all of it in `index_tree` (`graphwerk/indexing/python_ast.py`) re-parsing
  every file in both trees via `ast.parse` plus a per-function `ast.walk` for
  call-name extraction — on every call, whether or not the file changed.
- ~2.2s in building the per-node code view (`_code_view` →
  `build_code_view` → `highlight_lines`, tokenizing full source), computed
  unconditionally for every node. Of the 1451 nodes in this snapshot, 1177
  (81%) are `UNCHANGED` — and the sidebar only ever renders one node's code
  view at a time, so this work is thrown away for the overwhelming majority
  of nodes on every call.

This full recompute refires on every `/api/hash` poll (`static/app.js`,
`POLL_INTERVAL_MS = 1500`) that detects a changed mtime/size fingerprint —
which, while an agent session is actively editing files (the scenario Phase
2 is explicitly validating), is close to continuously. The roadmap's earlier
perf note ("Flask run ... `/api/graph` ~1s, no snapshot perf work needed at
mid-size") measured a single one-off load, not this repeated-during-a-live-
session case, which the agendabot dogfood run newly exposes.

A slow, repeatedly-recomputed snapshot directly undermines the product
concept's core loop — "the graph updates live" and "review at your own pace"
(docs/02-product-concept.md) — so this is in-phase hardening, not a detour.

## Decision

Add an in-process, content-fingerprint-keyed cache at the two hot spots
profiling identified, scoped to the lifetime of the existing long-lived
instances (`GraphService` and `ChangeSetBuilder` are each constructed once
per server process in `cli._serve` and live for its duration):

1. **File-level AST indexing.** `ChangeSetBuilder` caches each file's
   `FileIndex` keyed by `(root, rel_path, mtime_ns, size)` — the same
   fingerprint idiom `GraphService.state_hash()` already uses. A file whose
   fingerprint hasn't changed since the last `build()` is not re-parsed.
2. **Per-node code view.** The `_code_view` construction in
   `graphwerk/service.py` is cached keyed by the identity of
   `(base_text, staged_text)` it's built from, so an unchanged node's
   highlighted view is computed once rather than on every `snapshot()` call.

Both caches are purely additive memoization over existing pure functions —
same inputs, same outputs, just not recomputed when the input hasn't
changed.

## Alternatives considered

- **Push-based updates (SSE/websocket) instead of poll + full rebuild** —
  fixes the transport, not the redundant computation: an unchanged node's
  code view would still be rebuilt on every pushed update. Bigger
  architectural surface (new protocol, JS changes) for a problem caching
  solves more directly.
- **On-demand code-view endpoint** (compute `code` only when a node's
  sidebar is opened, not inline in the snapshot payload) — would also
  eliminate the 81%-wasted-work problem, and is arguably the more "correct"
  long-term shape, but changes the API contract and needs a JS-side fetch
  on node click. Larger than the current problem calls for; noted below as
  a deferred option if caching alone doesn't hold up at larger repo scale.

## Consequences

- A mostly-idle graph's `snapshot()` becomes near-free after the first
  call; during an active session, cost scales with files actually touched
  rather than whole-repo size.
- `ChangeSetBuilder` and the code-view path become stateful (in-memory
  cache tied to instance lifetime) — a first departure from being pure
  functions of `(base_root, staged_root)` / `(base_text, staged_text)`.
  Acceptable since both are already long-lived singletons per server
  process, not re-constructed per request.
- No invariant is touched: the differ still compares symbols by qualified
  name across two parsed trees (caching only skips redundant re-parsing of
  literally-unchanged files); `FileIndex`/`SymbolInfo` is unchanged; no new
  backend dependency; no JS-side logic added.

## Out of scope

- Push/websocket transport (noted above) — revisit only if push-based
  updates are independently wanted later (e.g. for other reasons), not as
  a perf fix.
- On-demand code-view endpoint / API contract change — a Phase 4/5-style
  reshape if caching alone proves insufficient at much larger repo scale.
- Algorithmic improvement of the call-graph `ast.walk` itself (beyond not
  redoing it for unchanged files) — the once-per-change cost is inherent
  to the call-edge model; not a bottleneck once redundant recompute is
  removed.
- Cache eviction / memory bounds for very long-running sessions — the
  cache grows with distinct file versions seen this process's lifetime;
  fine for a single dev session, revisit if long sessions show memory
  growth in practice.
