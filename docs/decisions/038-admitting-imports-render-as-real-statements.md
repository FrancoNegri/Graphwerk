# 038. Admitting imports render as the real import statements

Status: proposed
Date: 2026-07-17

## Context

ADR 035 (tickets 090/091, shipped 2026-07-17) gave the calls-edge panel an
"Imports admitting these calls" section: status chip + bare module name.
Immediate dogfood feedback from the user, same day: that entry should read
as *code* — the actual import statement from the caller's file
(`from agendabot.deps import get_classify_fn`), syntax-highlighted like the
call-pair code sections sitting directly above it in the same panel — not a
reconstructed module path.

This deliberately reverses part of a prior scope call. ADR 033 deferred
"line-level import extraction" because module-name granularity was all that
decision needed and the extension would touch the language-neutral
`FileIndex` contract; ADR 035 restated the deferral. What's changed is the
justification side: the panel now *shows* imports to the reviewer as a
primary review surface, and docs/02's core claim is that this tool replaces
flat-diff reading with the actual structural truth. A module name is a
derived value; the import statement is what's in the file. A review surface
that paraphrases code invites exactly the "go read the file to check"
round-trip it exists to remove.

Mechanically everything but the statement text already exists: the
extractor (`graphwerk/indexing/python_ast.py`) walks the very
`ast.Import`/`ast.ImportFrom` nodes whose text we need and keeps only the
module names; the panel already renders span-annotated code lines computed
in Python (`highlight_lines`, `build_code_view` line shape) through
`renderCode` in `static/app.js`.

## Decision

Capture the statement at index time, thread it through `via_imports` in the
code-line shape the panel already consumes, render with the existing code
renderer:

1. **`FileIndex`** (`graphwerk/models.py`) gains
   `import_statements: dict[str, tuple[str, int]]` — module name →
   (verbatim statement source text, 1-based start line). The extractor
   fills it from the same executable-node walk that fills `imports` (so
   `TYPE_CHECKING`-guarded imports stay excluded, ticket 065). If several
   statements import the same module, the first one wins — recorded here as
   the fidelity limit, revisit only if dogfooding hits it.

   This touches the language-neutral contract on purpose: "the source text
   of the statement that imports module M" is as language-neutral as
   `imports: set[str]` itself. A future extractor fills it the same way it
   fills `imports`; an extractor that leaves it empty degrades to today's
   module-name rendering (see 3).

2. **`GraphService.via_imports_entries`** (`graphwerk/service.py`) adds a
   `code` field to each entry: the statement rendered as the panel's
   existing code-line dicts `[{"text", "op", "line", "spans"}]` — one dict
   per source line for multi-line (parenthesized) statements, real line
   numbers from the captured start line, `spans` from `highlight_lines`,
   and `op` derived from the module's status (`added` → `add`, `deleted` →
   `del`, else `ctx`) so the existing gutter styling reads correctly. The
   statement is looked up in the caller's relevant tree's index (ADR 032
   branch: base for a `deleted` caller, staged otherwise) — the same index
   whose imports admitted the edge. `code` is omitted when no statement
   text is available.

3. **Frontend** (`static/app.js`): the admitting-imports section renders
   each entry's `code` through the existing `renderCode`, keeping the
   status chip; entries without `code` fall back to today's module-name
   text (which also keeps the shared `renderImportEntry` usage in the
   imports-edge panel working unchanged). Render-only, per ADR 005.

## Alternatives considered

- **Frontend synthesizes `import <module>` from the module name** — no
  backend change at all, but it fabricates a line that may not exist in the
  file (`from x import y as z` becomes `import x`): fake code on a review
  surface whose whole pitch is showing the real thing. Rejected.
- **Service-side line scan** — service re-reads the caller's source and
  regex-matches import lines, leaving `FileIndex` untouched. Creates a
  second, weaker import parser outside `indexing/` that will disagree with
  the AST walk (multi-line statements, TYPE_CHECKING blocks, comments), and
  puts parsing in a layer that's supposed to consume parse results.
  Rejected.

## Consequences

- The calls panel becomes uniformly code: call pairs show real code,
  their admitting imports show real code, one visual language.
- `FileIndex` grows one field — the deliberate contract touch above. New
  extractors have one more thing to fill, with a graceful fallback if they
  don't.
- Payload grows by statement text + spans per cross-file call edge entry
  (deduped client-side as before) — same negligible-at-dogfood-scale
  category as ADR 035's addition.
- First-statement-wins is a known fidelity limit for modules imported by
  multiple statements.

## Out of scope

- The imports-edge click panel (`showEdgeImports`) keeps chip + module
  name. Giving it the same treatment is a natural one-ticket follow-up
  once the same data flows on imports edges — deferred until dogfooding
  asks.
- Alias *analysis* (resolving what `as z` binds) — capture is verbatim
  text only.
- Relative-import dot-level resolution — ticket 054, separate.
- Collapsing multiple statements per module — first wins, above.
