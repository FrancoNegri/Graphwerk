# 041. Paired test-file placement: test pill anchored below its source file's center

Status: proposed
Date: 2026-07-17
Extends: 005

*Amended 2026-07-17 (ticket 111 dogfood verification):* the mirror-key
algorithm below only drops a file's literal top-level directory, which
turns out to pair nothing at all on the agendabot dogfood repo — its
src-layout (`src/agendabot/webhook.py` vs `tests/test_webhook.py`) leaves
an extra `agendabot` package-root segment on the source side that the flat
`tests/` tree never mirrors. Decision 1 is extended: the mirror key drops
the wrapper directory *and* the package-root segment after it, reusing
`group_for_path`'s existing `src`/`lib` wrapper-directory set (ADR 021)
rather than inventing a second convention for the same concept. This
recovers pairing for the many agendabot files that already follow the
naming convention 1:1 once the package root is discounted (`webhook.py`,
`classifier.py`, `cron.py`, `store.py`, `validators/adapter_resets.py`,
etc.) — it does not help the ones with looser test names (`mock.py` vs
`test_mock_adapter.py`), which stay unpaired by design (Decision, point 1:
"no arbitrary tie-break"). Ticket 113 implements this. Non-wrapper-rooted
repos (this repo's own tree, `graphwerk/...` vs `tests/...`) are unaffected
since they have no wrapper segment to drop.

## Context

`assign_layers` (`graphwerk/layout.py`) gives every file an import-depth
layer by longest path over the import graph (ADR 002/022). Test files'
*own* import edges are already dropped from that graph (ADR 023 / ticket
064), so as to not let test-sourced edges pollute source-file layering —
but that leaves every test file with no adjacency of its own. With no
edges to sweep against, the barycenter ordering (ADR 008) does nothing for
them, and they all land at layer 0: the same band as genuine entry points,
with no signal distinguishing "this is a real root" from "this is a test
file that happens to have no adjacency." ADR 010 already documented the
consequence on a real repo (agendabot dogfood, "the widest band is 10 src +
22 tests chained in one 32-chip row"). The user's own description matches
that exactly: tests "loom over the graph in a hard to understand blob."

This is squarely Phase 2's Scale UX line (docs/04-roadmap.md: "collapse/
expand file boxes... so big repos open readable") and serves the product
concept's structural-context promise (docs/02: the graph should show
*where* something sits, not just that it changed) — reviewing a real
session's test coverage is part of Phase 2's exit criterion.

This repo's own tree demonstrates the convention cleanly:
`tests/test_layout.py` ↔ `graphwerk/layout.py`,
`tests/indexing/test_python_ast.py` ↔ `graphwerk/indexing/python_ast.py`,
`tests/staging/test_differ.py` ↔ `graphwerk/staging/differ.py` — directory
structure mirrors 1:1 once the `tests/` prefix and `test_`/`_test` filename
affix are stripped.

## Decision

1. **Deterministic filename-convention pairing, server-side.** A new pure
   function in `graphwerk/layout.py` computes a mirror key per file path:
   drop the file's top-level directory, and — for test files only — also
   strip a leading `tests`/`test` path segment and a `test_`/`_test`
   filename affix. Test files are paired with the source file sharing the
   same mirror key. No match, or more than one candidate sharing a key,
   means unpaired — no arbitrary tie-break.
2. **Unpaired test files keep today's behavior, unchanged.** `conftest.py`,
   cross-module integration tests, or anything the convention can't
   resolve stays exactly where it renders today (its own root-layer slot).
   Only files with a clean pair move.
3. **Paired test files drop out of the normal file-layer graph.** They get
   no `layer`/`order` from `assign_layers` — the same treatment their own
   import edges already get (ADR 023), now extended to the node itself,
   since they're going to be anchored directly instead.
4. **`GraphNode.paired_file` payload field**, set only on paired test-file
   nodes (omitted when null, same convention as `is_test`), carrying the
   matched source file's id. Computed purely from `path`, so it costs
   nothing for future non-Python extractors (mirrors how `group`/`is_test`
   already derive for free — CLAUDE.md's `FileIndex`/`SymbolInfo`
   language-neutral contract stays untouched; this is a layout concern, not
   an indexing one).
5. **Client-side post-layout position override**, not an fcose constraint.
   After the fcose layout settles, `app.js` sets each paired test node's
   position directly: left edge at its file node's horizontal center,
   fixed gap below the file's bottom edge. Presentation-only math consuming
   a precomputed field — the same split ADR 005 already draws (JS stays
   thin, layout logic is Python and pytest-covered).
6. **No other visual change.** Paired test pills keep their own directory
   tint (ADR 010) — no shared-tint or connector-line treatment. No change
   to `hide-tests`, `changed-only`, or `is_test` semantics. Both explicit
   user calls for this round.
7. **No collision-avoidance reservation.** The paired test pill isn't given
   extra reserved width in its band; on a dense graph it may overlap a
   neighboring pill. Accepted for this increment (explicit user call) —
   see Out of scope.

## Alternatives considered

- **Express the offset as an fcose `relativePlacementConstraint` chain**
  (glue the test to its file the way per-file function sub-bands already
  work) — rejected: fcose's constraint gap is edge-to-edge between two
  nodes' facing sides, not "half of my own width." There's no primitive
  for "my left edge equals your center," so this would need a fudge-factor
  gap tuned to a typical pill width, which drifts wrong the moment a label
  is longer or the file is expanded to show its symbols.
- **Reserve extra horizontal width per paired column** so neighbors can
  never overlap — the more robust answer, but explicitly declined for this
  round; noted below as the natural follow-up.
- **Import-based pairing** (match a test file to the module it imports
  most/first) — rejected: test files commonly import several modules, so
  "the" pair is ambiguous without more heuristics. The filename convention
  already resolves this repo's entire tree with zero ambiguity.

## Consequences

- A reviewer sees each test directly under the code it exercises instead
  of hunting through the layer-0 blob for it; unpaired tests are
  unaffected — same position and behavior as today.
- One more precomputed, pytest-covered field in Python; `app.js` only
  consumes it — extends the ADR 005 split.
- Paired test pills lose participation in barycenter/order optimization
  for their old slot — but they had no adjacency there to optimize in the
  first place (that's the bug being fixed), so nothing meaningful is lost.
- Possible pixel overlap with a neighboring band pill on dense graphs,
  since no reservation logic is added yet — a known, accepted rough edge
  for this round, not a regression from today's blob.
- Touches no architecture invariant: pairing is Python/stdlib-only,
  derived from `path`, and the client only consumes a precomputed field.

## Out of scope

- Horizontal collision/overlap avoidance for paired columns — revisit if
  it proves disruptive once shipped; natural next increment under Phase
  2's Scale UX line.
- Visual tie (shared tint or a connector line) between a paired file and
  its test — explicitly declined this round.
- Multi-test-per-file or multi-file-per-test pairing — the mirror-key
  match only ever proposes one candidate; anything ambiguous falls back
  unpaired rather than guessing.
- Symbol-level (function-to-test-function) pairing — this decision is
  file-pill granularity only, matching the request.
- Non-Python languages — the mirror-key convention is generic over `path`
  strings so it should carry over for free, but only Python is
  exercised/tested here, matching the single-extractor state today.
