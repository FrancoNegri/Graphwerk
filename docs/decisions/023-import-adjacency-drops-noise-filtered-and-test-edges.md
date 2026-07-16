# 023. Import adjacency must survive noise-filtered nodes and ignore test-sourced edges

Status: proposed
Date: 2026-07-16

## Context

ADR 022 (tickets 061/062, implemented but not yet committed) flipped layering
to anchor entry points at layer 0. Dogfooding that fix against agendabot
(this session) surfaced a new, sharper gap: `webhook.py` — the file the
repo's own FastAPI app mounts — lands at layer 1, while `booking_actions.py`,
a file three imports deep (`webhook.py -> handlers.py ->
booking_actions.py`), lands at layer 0. Root-caused by tracing the actual
`/api/graph` output against agendabot's real import statements:

1. **Noise-filtered files silently break the import chain.**
   `GraphService.snapshot()` skips creating a `GraphNode` for any unchanged
   file with no extracted symbols (`service.py:71-72`, "e.g. empty
   `__init__.py` — pure noise in the graph", present since v1). But the
   symbol extractor only extracts function/class defs — a file that's
   entirely top-level imports plus a module-level dict (agendabot's
   `handlers.py`: a registry of `HANDLERS = {...}` built from imported
   functions, zero `def`s) gets caught by the same filter despite being a
   real link in the import chain. `_add_import_edges` still emits the edges
   through it (`webhook.py -> handlers.py`, `handlers.py ->
   booking_actions.py`) into `snap.edges`, but `layout.py`'s
   `_import_adjacency` only keys `imported_files_of` off `nodes` with
   `kind == "file"` and then requires *both* endpoints to already be keys
   before counting an edge — so both edges through `handlers.py` are
   dropped from the layering computation entirely. `booking_actions.py`'s
   only real incoming edge vanishes, so it looks like a root and gets
   layer 0 — despite the repo genuinely reaching it only through two other
   files.

2. **Test-file edges count the same as production edges.**
   `tests/test_webhook.py` imports `webhook.py` (normal — that's what makes
   it a test). Nothing in `_import_adjacency` distinguishes that from a
   production import, so it demotes `webhook.py` from layer 0 (a root — no
   *production* file imports it) to layer 1. Any well-tested entry point
   gets pushed down by its own test suite, which is close to universal:
   the better a repo's coverage, the less reliable layer 0 becomes at
   marking real entry points. This directly undercuts what ADR 022 was
   written to fix.

Both are dogfood findings against the same real repo, in the same review
pass, continuing the thread ADR 022 started — not a detour. They belong in
Phase 2 (`docs/04-roadmap.md`): the roadmap's own exit criterion is
reviewing a real Claude session end to end, and "is this near where the app
starts" (docs/02, structural context) is exactly the promise a wrong layer-0
assignment breaks.

## Decision

Both fixes stay inside `_import_adjacency` in `graphwerk/layout.py` — no
`service.py` or `static/app.js` changes.

1. **Build `imported_files_of` from the union of file nodes and edge
   endpoints, not from nodes alone.** Seed it from displayed file nodes (as
   today, so an isolated file with no edges still gets a layer), then for
   every `imports` edge, `setdefault` *both* endpoints into the map before
   recording the edge — instead of requiring both to already be present.
   A noise-filtered file's id becomes a "phantom" adjacency key: it
   participates in propagating layers through it, but since it was never
   added to `nodes`, `assign_layers`'s final `layer_by_id.get(node.id)`
   lookup never surfaces it, so it still doesn't render as its own node.
2. **Drop edges sourced from a test file before building the adjacency.**
   A file counts as a test file by the same convention pytest itself uses
   for discovery: a `tests/`- or `test/`-named path segment, or a filename
   matching `test_*.py`/`*_test.py`. An edge whose *source* is a test file
   is excluded from `imported_files_of` entirely — a test importing
   `webhook.py` doesn't stop `webhook.py` from being a root. Test files
   remain nodes (existing noise filter — a test file always has a
   `def test_...`, so it's never symbol-less) and, having no *production*
   importers, land at layer 0 themselves, same as today.

## Alternatives considered

- **Stop noise-filtering files out of `snap.nodes`** — would sidestep
  problem 1 by never dropping the node in the first place, but reintroduces
  the clutter the filter exists to prevent (empty `__init__.py`, and now
  every re-export/constants-only module too), fighting the roadmap's own
  "Scale UX ... readable" goal instead of serving it. Rejected.
- **Build a separate full-repo import adjacency in `service.py`, pass it
  into `assign_layers` alongside the display nodes** — also fixes problem
  1, but duplicates the edge-endpoint bookkeeping `layout.py` already does
  and adds a new parameter crossing the service/layout boundary for
  something the edges already fully describe. Rejected — smaller diff wins.
- **Leave test edges in the adjacency (status quo)** — structurally
  consistent with "layer 0 = nothing imports it," but the dogfood evidence
  shows it fails the actual goal (docs/02 structural context) for any
  entry point with test coverage, which is most of them. Rejected.
- **Config-designated entry points** (already deferred once in ADR 022's
  out-of-scope) — still no evidence this repo needs manual override; both
  fixes here are structural heuristics, not per-repo configuration.

## Consequences

- `booking_actions.py` and any file reachable only through a symbol-less
  intermediate file get their real (deeper) layer back.
- `webhook.py` and any other file imported only by its own tests becomes a
  root again, converging with the repo's other true entry points at layer 0
  — the concrete case ADR 022 was written for.
- The test-file heuristic is a path convention, not a parsed signal; a repo
  that names test files unconventionally (no `tests/`/`test/` segment, no
  `test_*`/`*_test` filename) won't get the exclusion. No evidence either
  dogfood repo needs more than this.
- Touches no invariant: contained in `graphwerk/layout.py`, stdlib-only, no
  new cross-layer coupling, no change to the differ/models/apply contracts.

## Out of scope

- Any change to the function/call adjacency (`_call_adjacencies_by_file`) —
  the noise filter only ever drops *file* nodes; individual functions are
  always added when `info` exists, so this problem doesn't reach them, and
  test files' own internal call graphs are unaffected either way.
- Config-designated entry points (still deferred, per ADR 022).
- Any UI/rendering change — layer semantics from ADR 022/tickets 061-062
  are unchanged; this only fixes which edges feed the same computation.
