# 064. Changed-method code view surfaces the module imports it actually uses

Status: proposed
Date: 2026-07-22

## Context

Dogfooding a real agendabot session against `changed-methods` code-display
mode (ADR 051, now the default per ADR 053) surfaced a gap. Reviewing
`src/agendabot/test_router.py`'s `TestOnlyRouter.__init__` — a changed
method — renders only that method's own line range: `self.router =
APIRouter()`, `datetime.fromisoformat(...)`, `-> Any` all appear with no
statement in view that brings `APIRouter`, `datetime`, or `Any` into scope,
because those are bound by module-level imports (`from fastapi import
APIRouter`, `from datetime import datetime`, `from typing import Any`)
outside the method's own line range, which `changed-methods` mode never
renders. (The method's *own* local imports — `from pydantic import
BaseModel as _BaseModel`, `from agendabot.classifier import
ClassifierResult`, `from agendabot.dependencies import _mock_intents,
get_calendar` — are already visible today, since they're literal lines
inside the method's own source slice; only the module-level ones are
missing.)

This is exactly the "review surface that omits a real statement invites a
go-read-the-file round trip" problem ADR 038 was written to fix — except
ADR 038/039/052 wired that fix only into the *calls panel* (an import that
admits a cross-file `calls`/`uses` edge between two symbol nodes). It
doesn't apply here: `APIRouter`/`datetime`/`Any` are external-library names
with no graph node of their own, so there's no edge to attach a
`via_imports` entry to. The gap is specific to a symbol's own per-method
`code` view, which ADR 051 defined as exactly the symbol's own extracted
source with nothing else — that decision didn't consider a method
referencing names bound outside its own span.

This directly serves docs/02's "structural context" pitch (a reviewer
shouldn't have to leave the reviewing surface to answer "where does this
name come from") and matches Phase 2's dogfooding exit criterion — this is
a real gap a real session's review surfaced, not a hypothetical.

## Decision

Attribute each changed leaf symbol's own module-level import dependencies,
the same way ADR 062 already attributes its module/class-variable
dependencies (`SymbolInfo.uses`), and render them alongside its code in
`changed-methods` mode:

1. **`graphwerk/indexing/python_ast.py`**: build a per-file binding table of
   `bound name -> (statement text, line)` from *module-level* (depth-0)
   `Import`/`ImportFrom` nodes only — not the nested/local ones already
   captured by `import_statements` at any depth. `as`-aliases bind their
   alias name; a plain `import pkg.sub` binds `pkg`. Wildcard imports
   (`import *`) bind nothing (no specific name to attribute) and are
   skipped, same posture as ADR 052's other precision gaps.
2. **`graphwerk/models.py`**: `FileIndex` gains the binding table (e.g.
   `imported_names: dict[str, tuple[str, int]]`). `SymbolInfo` gains
   `imports_used: set[str] = field(default_factory=set)` — mirrors `uses`
   exactly: bound names a function/method body references (`ast.Name`
   loads, same walk `_used_global_names` already does for variables) that
   aren't shadowed by a name the symbol binds itself (its own parameters,
   local assignments, nested defs, or its own local imports — all of which
   already render as part of its own source, so re-showing them would be
   pure duplication).
3. **`graphwerk/service.py`**: when building each leaf symbol's
   `GraphNode`, resolve `imports_used` against `FileIndex.imported_names`
   and render each match as a real statement, reusing `_statement_code_lines`
   (ADR 038's existing helper — same line-view shape `renderCode` already
   consumes) so the new block gets identical highlighting/diff treatment
   for free. Carried on the node as a new field (e.g. `used_imports`).
4. **`static/app.js`**: `renderChangedMethods` (ADR 051) renders this block
   for each changed leaf symbol, above its own `renderCode(symbol.code)`,
   using the same `import-entry`-style markup the calls panel already uses
   for admitting imports (`renderCallPair`) — one visual language for "an
   import statement attached to a piece of code," not two.

## Alternatives considered

- **Reuse the calls-panel's `admitting_entry`/`via_imports` machinery
  directly** — that machinery is edge-oriented: it answers "which import
  admits *this call* to *that resolved file*," and requires
  `ModuleFileResolver` to resolve the module to a repo file/symbol node.
  `APIRouter`/`datetime`/`Any` resolve to nothing (external libraries, no
  node in the graph) — there's no edge to hang a `via_imports` entry off
  of. The question here ("what names does this method's body use that
  come from an import, resolved or not") is a different shape of problem;
  forcing it through the edge-resolution path would either drop every
  external-library case (the majority of what dogfooding actually hit) or
  require inventing phantom edges to unresolvable targets. Rejected.
- **Frontend heuristic — search the file's header text for each name the
  method's code block mentions** — no backend change, but the frontend
  never receives full file source today, only the pre-selected `code`
  views already assembled server-side (ADR 051's own rejection of backend
  slicing applies in reverse here too); this would also violate
  thin-JS/ADR 005 for what's fundamentally a name-resolution question.
  Rejected.
- **Do nothing — leave it to "go check the file's imports yourself"** —
  cheapest, but this is precisely the round-trip docs/02 and ADR 038 both
  exist to remove, and dogfooding already produced a concrete case where
  it costs real review time. Rejected.

## Consequences

- Makes `changed-methods` mode's per-symbol view self-contained: a
  reviewer sees every name-binding a changed method depends on without
  leaving that method's block, matching the calls panel's existing
  standard for "attach the real statement, don't paraphrase."
- `SymbolInfo` grows one more attribution set (`imports_used`), directly
  parallel to `uses` (ADR 062) — same computation shape, same
  degrade-gracefully-to-empty-set contract for any future non-Python
  extractor (the Markdown extractor already has no imports concept and
  naturally emits nothing here).
- `FileIndex` grows one more field (module-level name bindings) — additive,
  mechanical, no change to any existing field's meaning.
- No invariant touched: no hunk-to-symbol mapping (this is name-reference
  matching within a symbol's own already-parsed AST, the same class of
  heuristic `uses`/ticket 065's caller-span check already are, not line
  slicing); `FileIndex`/`SymbolInfo` stay language-neutral; no new backend
  dependency; Python-side computation, JS stays a payload consumer.
- Slightly increases the size of each rendered changed-method block, but
  only for methods that actually reference outside-scope import bindings —
  most changed methods (including agendabot's own nested nested defs that
  only use their own parameters and locally-imported names) render nothing
  extra.

## Out of scope

- `changes-only` mode — deliberately bare by ADR 051's own design (zero
  surrounding context is the point of that mode); not touched.
- `full` mode — the whole file/class view already includes the real header
  imports as part of the file text itself; nothing to add.
- Imports bound only inside a *different* function/method elsewhere in the
  file (function-local imports outside this symbol's own span) — genuinely
  out of scope for this symbol, not just imprecise; only module-level
  (depth-0) bindings are attributable here.
- Wildcard (`import *`) resolution — no specific bound name to attribute;
  same deferred-until-dogfooding-hits-it posture as ADR 052.
- Any change to the calls panel / `admitting_entry` / `via_imports`
  (ADR 038/039/052) — untouched, separate mechanism, separate problem
  shape (see Alternatives).
- Multi-hop/transitive import reachability (ADR 048) — irrelevant; this is
  same-file, single-hop name binding, no cross-file module resolution
  involved.
