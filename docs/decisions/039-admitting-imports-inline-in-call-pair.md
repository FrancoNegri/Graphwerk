# 039. Admitting imports render inside the call pair's caller section

Status: proposed
Date: 2026-07-17

## Context

ADR 035 gave the calls-edge panel an "Imports admitting these calls"
section; ADR 038 (tickets 100-102, shipped 2026-07-17) made those entries
render as the real import statements. Immediate dogfood feedback from the
user, same day: the statement shows up in the right panel but the wrong
*place* — a panel-level section sitting under **all** the call-pair
dropdowns, when what the reviewer wants is to see the import **inside the
appropriate caller/callee dropdown** it belongs to.

The current layout has a real disconnect: each `<details>` pair (ADR 028)
is deliberately self-contained — "a pair you open is always the pair whose
code you see" — yet the import that admits that specific pair renders
outside every dropdown, deduped across pairs (`dedupedViaImports`,
`static/app.js`). With several pairs collapsed onto one edge, the reviewer
opens a pair and then has to visually re-join it with the right entry in a
shared list below. That's the same "unlinked information" smell ADR 035
existed to remove, one level down.

Structurally the admitting import always belongs to the **caller's side**:
it is a statement in the caller's file, resolved from the caller's
relevant tree (ADR 032/034). And the data is already per-pair — each
`calls` edge carries its own `via_imports` with statement code lines
(ADR 038); the panel-level section is a render-time union.

## Decision

Move the admitting-import entries from the panel-level section into each
call-pair dropdown, rendered in the caller's section of the pair body:

1. **Frontend** (`static/app.js`): `renderCallPair` receives the pair's
   own `via_imports` and renders each entry (status chip + `renderCode`
   statement, `renderImportEntry` markup unchanged) at the top of the
   caller's `<section>` — the import is the first thing shown, above the
   caller's code, because that is where it sits in the caller's file. The
   panel-level "Imports admitting these calls" section and
   `dedupedViaImports` are removed. Render-only, per ADR 005.
2. **Service** (`graphwerk/service.py`): `via_imports_entries` marks each
   entry `in_caller_code: true` when the statement's start line falls
   within the caller symbol's own span (`lineno`..`end_lineno` in the
   caller's relevant index — nested imports, ticket 065, can live inside
   the very function that makes the call). The frontend skips rendering
   marked entries: the statement is already visible inside the caller's
   code block, and repeating it directly above would show the same line
   twice. The containment check is Python-side on purpose (thin-JS rule).

## Alternatives considered

- **Keep the panel section and also render per-pair** — duplication with
  no reader benefit; the user asked for the import *in place of* the
  detached list, not in addition to it. Rejected.
- **Merge the statement lines into the caller's code view server-side**
  (one continuous code block: import line, gap marker, function body) —
  the most "one piece of code" rendering, but the caller's code view is a
  node-level artifact shared by every pair and panel that shows the node;
  a per-pair merged variant means duplicating code views onto edges and
  coupling `codeview.py` to edge construction. Rejected for now; worth
  revisiting only if the stacked blocks read badly in practice.
- **Frontend-only move (no `in_caller_code` flag)** — one file touched,
  but a nested import inside the caller would render twice with no way to
  tell, or the dedupe check (line-range containment against the caller's
  code lines) would become logic in untested JS. Rejected per the
  standing thin-JS rule.

## Consequences

- Every open dropdown is now fully self-contained: label, admitting
  import, caller code, callee code — nothing to cross-reference.
- Pairs sharing a caller file repeat the same import entry when opened —
  acceptable: dropdowns are closed by default (ADR 028) and the
  repetition is the point (each pair tells its own whole story).
- `via_imports` entries grow one boolean; payload delta negligible.
- The imports-edge panel (`showEdgeImports`) is untouched — it still uses
  `renderImportEntry` directly, which keeps working unchanged.
- No invariant touched: logic (span containment) stays in Python with a
  test; JS remains a payload consumer; models/differ untouched.

## Out of scope

- The imports-edge click panel's rendering (chip + module name) — same
  deferral as ADR 038.
- Merged single-code-block rendering — see Alternatives; revisit on
  dogfood feedback.
- Alias analysis, multi-statement-per-module fidelity, relative-import
  dot-level resolution (ticket 054) — all unchanged from ADR 038.
