# 033. Import edges carry per-module status; clicking one shows only the pertinent imports

Status: accepted
Date: 2026-07-17

*Amended 2026-07-17:* the "line-level import extraction — deferred"
alternative below is partially reversed by
[ADR 038](038-admitting-imports-render-as-real-statements.md): the
extractor now captures verbatim import statement text (for the calls
panel's admitting-imports section). Aliasing analysis stays deferred, and
this ADR's module-name granularity for edge status is unchanged.

## Context

Phase 2's real-repo hardening goal (docs/04-roadmap.md) is to fix what the
differ/indexer trips on during dogfooding. This is the imports-side sibling
of ADR 032 (which fixed a related gap on `calls` edges): dogfooding surfaced
that when an AI-generated change is *purely* import surgery — a symbol moves
to a new module and the caller's import statement updates, a common
AI-refactor shape — the graph gives the reviewer no structural signal for
why the file turned `modified`. Every symbol inside it is still `unchanged`,
so there's nothing to click that explains the change; the reviewer has to
fall back to reading the file's full text diff and spotting the import line
themselves. That's exactly the flat-diff-reading experience docs/02 says
this tool exists to replace ("structural context," not text).

The root cause is that `calls` edges and `imports` edges are treated
asymmetrically in `GraphService` (`graphwerk/service.py`):

- `calls` edges get a real per-edge `Status` (ADR 016): `_mark_edge_status`
  borrows the *target* symbol's status, so a caller pointing at a changed
  function renders colored and visible; a caller pointing at unchanged code
  renders gray and hover-only (ADR 020, `edge[status='unchanged']` in
  `static/app.js`). Clicking a `calls` edge opens a panel (ADR 017/028)
  listing exactly which call pairs it collapsed, each showing caller/callee
  code.
- `imports` edges never get a real status. `_add_import_edges` builds one
  edge per module name in `(change.staged or change.base).imports` — the
  *current* tree's import set only, with no base/staged comparison — and
  leaves `GraphEdge.status` at its dataclass default, `Status.UNCHANGED`.
  Two consequences: every import edge is permanently hover-only (there's no
  way to distinguish a brand-new import from one that's existed for years),
  and clicking one does nothing — `static/app.js` only binds a tap handler
  to `edge[kind='calls']`. Worse, because the edge is built from a single
  tree's import set rather than a union, a *removed* import (present in
  base, gone from staged) doesn't even produce an edge to hide — it just
  silently disappears, the mirror of the phantom-edge problem ADR 032 fixed
  for `calls`.

## Decision

Extend the same technique the differ already uses for symbols — compare
base and staged by identity, across both trees — to imports, one level
coarser (module name instead of qualified name):

1. **`ChangeSetBuilder.build()`** (`graphwerk/staging/differ.py`) computes
   `change.imports: dict[str, Status]` alongside `change.symbols`, over the
   union of `base.imports | staged.imports`: staged-only → `ADDED`,
   base-only → `DELETED`, in both → `UNCHANGED`. Added/deleted files reuse
   the same all-`ADDED`/all-`DELETED` handling already applied to their
   symbols.
2. **`GraphEdge`** (`graphwerk/models.py`) gains `module: str | None`, set
   only for `imports`-kind edges — the module name responsible for that
   edge, so the UI can say *which* import changed, not just that one did.
3. **`_add_import_edges`** (`graphwerk/service.py`) iterates the union of
   both trees' import sets (fixing the silent-disappearance bug above),
   looks up each module's status in `change.imports`, and sets it on the
   `GraphEdge` along with the module name.
4. **Frontend** (`static/app.js`): the existing hover-reveal rule
   (`edge[status='unchanged']`, ADR 020) already starts working correctly
   for imports once real statuses flow through it — no new CSS rule needed
   there. What's missing is (a) status-based coloring for `imports` edges,
   currently hardcoded to a flat slate color, and (b) a click handler
   (`edge[kind='imports']`), mirroring `showEdgeCalls`, that lists the
   added/removed module names for that file pair — deliberately *not* the
   full file diff (already one click away, via the file node itself), so
   "show me the pertinent imports" gets a small, direct answer instead of
   requiring the reviewer to find the import line inside a whole-file diff.
   Per CLAUDE.md, this stays payload-driven: the backend already supplies
   `status` and `module` per edge, so the JS side is the same
   fuse-and-render pattern `renderCallPair` already does, not new logic.

## Alternatives considered

- **Node-level import diff only** — add an `import_diff` field to the file
  `GraphNode` and surface it in the sidebar when the file is selected, no
  edge changes at all. Cheaper (no new edge-status plumbing, no click
  handler), but doesn't fix the actual asymmetry: `calls` edges already
  answer "why is this connection here" per-edge, and leaving imports
  node-only means the reviewer has to already have the file selected rather
  than reading the answer directly off the edge they're looking at on the
  graph. Rejected — it treats the symptom (no imports summary anywhere) but
  not the inconsistency this ADR is about (edges lie about their own
  status).
- **Line-level import extraction** (track exact source line, aliasing,
  `from x import a, b` multi-name lines) so the click panel shows real
  source text instead of a reconstructed module name — more faithful, but
  needs a new field on the language-neutral `FileIndex` contract for
  line-level import records, which is a bigger change than this problem
  calls for. `FileIndex.imports` is already a flat `set[str]` of module
  names; that's the full granularity this ADR needs. Deferred.

## Consequences

- Import edges become colored and visible-by-default exactly when they
  represent a genuine add/remove, mirroring how `calls` edges already work
  — a reviewer scanning the graph sees "this file's connection to that file
  is new" the same way they already see "this call is new."
  Long-standing, unchanged imports stay hover-only clutter, unchanged from
  today.
  Files whose only change is import surgery now carry graph-level signal
  instead of being visually identical to any other `modified` file.
- Fixes a latent bug as a side effect: a removed import previously produced
  no edge at all (silently dropped); it now produces a `deleted`-status
  edge, consistent with how a removed call or a deleted symbol is
  represented elsewhere.
- No invariant is stretched: this is still a set comparison over
  `FileIndex.imports` (module names), not hunk-to-symbol mapping; no new
  backend dependency; `FileIndex`/`SymbolInfo` stay the language-neutral
  contract (the new `GraphEdge.module` field lives on the graph-layer
  model, not the indexer's).

## Out of scope

- Extending blast radius (`_mark_affected` / the `affected` status) to
  imports — a file that merely imports a changed file does not turn
  `affected` the way a caller of a changed function does. Whether
  "structurally downstream via import" should mean the same thing as
  "structurally downstream via call" is a separate product question, worth
  its own `north-star` pass if it comes up.
- Line-level import text / aliasing (Alternative 2 above) — module-name
  granularity is what ships here.
- Any change to `calls`-edge behavior — untouched by this decision.
