# 035. Call edges carry the imports that admit them; the calls panel shows them

Status: proposed
Date: 2026-07-17

## Context

Phase 2's real-repo hardening goal (docs/04-roadmap.md), continuing the
ADR 032/033/034 dogfood lineage. On the live agendabot dogfood graph, the
collapsed `webhook.py → deps.py` calls edge's click panel reads exactly:

> Calls collapsed onto this edge
> `added` twilio_webhook → get_classify_fn

The reviewer's next question is structural: *which import makes this call
reachable?* (`get_classify_fn` moved out of `webhook.py` into `deps.py`,
and `from agendabot.deps import get_classify_fn` was added — the classic
AI-refactor shape ADR 033/034 were built around.) The reviewer cannot see
that from the calls panel, and in practice cannot see it at all:

- ADR 033 put per-module import status on the **imports edge** and gave it
  its own click panel — but imports edges are a *separate parallel edge*,
  and the imports view defaults **off** (`showImportsView = false`,
  `static/app.js`; ticket 048 deliberately turned only the calls view on
  by default). ADR 033's "visible-by-default when changed" consequence
  only holds after the reviewer finds and flips the imports toggle.
- Even with the toggle on, the information sits on a different edge than
  the one the reviewer is inspecting. Nothing links "this call pair" to
  "the import that admits it."

Meanwhile the backend already computes exactly this link and throws it
away: since ADR 034, `_add_call_edges` resolves the caller's relevant
tree's imports through `ModuleFileResolver` and only wires a target
reachable via those imports — it knows *which module* admitted each
cross-file call edge at the moment it creates it, and per-module status
already exists in `change.imports` (ADR 033, ticket 082).

## Decision

Make the admitting import part of the call edge itself, end to end:

1. **`GraphEdge`** (`graphwerk/models.py`) gains `via_imports:
   list | None` — for `calls`-kind edges only, the module name(s) from the
   caller's relevant tree (base for a `deleted` caller, staged otherwise,
   per the existing ADR 032 branch) whose resolution admitted the target's
   file, each with that module's status from `change.imports`. `None` for
   imports edges and for same-file calls (which need no import).
2. **`_add_call_edges`** (`graphwerk/service.py`) records those modules
   when it wires a cross-file edge, from the module→file resolution it
   already performs — no new resolution work, just keeping what it
   currently discards.
3. **Frontend** (`static/app.js`): the calls-edge click panel renders a
   deduped "imports for these calls" section under the call pairs,
   reusing the `renderImportEntry` markup ADR 033 introduced (status
   chip + module name). Payload-driven fuse-and-render, same as
   `renderCallPair` — no new JS logic beyond dedupe-and-render.

## Alternatives considered

- **Frontend-only join** — `showEdgeCalls` scans the raw payload for
  imports edges between the same file pair and renders those. No backend
  change, but it puts real matching logic in untested JS (ADR 005 / the
  standing thin-JS rule: logic lives in Python, app.js consumes payload
  fields), and it's an approximation: it would list every import module
  linking the two files from *either* tree, not the module(s) that
  actually admitted these calls under the ADR 032/034 tree branch (e.g. a
  base-only, now-deleted module would show up under a staged call it
  never admitted). Rejected.
- **Flip the imports view on by default** — one line, and changed import
  edges would at least render. But it reverses ticket 048's deliberate
  calls-only default, and still leaves the answer on a different edge
  than the one the reviewer is asking about — the call pair and its
  admitting import stay unlinked. Rejected as the fix for *this* problem;
  revisiting the default is its own small UX call if dogfooding keeps
  hitting it.

## Consequences

- The calls panel answers the reviewer's follow-up in place: a call into
  moved/new code shows the import that backs it, with the same
  added/deleted/unchanged chip the imports panel uses — "this call is new
  *and* the import enabling it is new" becomes one glance.
- `GraphEdge` grows a second kind-specific field (`module` is
  imports-only, `via_imports` is calls-only). Acceptable for now;
  if a third kind-specific field ever appears, splitting the edge model
  per kind becomes worth a look.
- Slightly larger `/api/graph` payload (a short module list per
  cross-file call edge, duplicated across pairs sharing a file pair) —
  negligible at dogfood scale, and the client dedupes at render time.
- No invariant touched: resolution data already exists (ADR 034), the
  differ is unchanged, `FileIndex`/`SymbolInfo` stay untouched (the new
  field is graph-layer), no new dependency, logic stays in Python with
  the JS side render-only.

## Out of scope

- Changing the imports-view default visibility (see Alternatives).
- Extending blast radius through imports — still deferred, per ADR 033.
- Line-level import text / aliasing — still deferred, per ADR 033.
  *(Reversed for statement text by
  [ADR 038](038-admitting-imports-render-as-real-statements.md),
  2026-07-17, after dogfooding this panel; aliasing analysis stays
  deferred.)*
- Relative-import dot-level resolution — ticket 054, separate.
