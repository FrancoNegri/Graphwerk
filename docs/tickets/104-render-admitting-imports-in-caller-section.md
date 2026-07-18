# 104. Calls panel renders admitting imports inside each pair's caller section

Status: done
Decision: docs/decisions/039-admitting-imports-inline-in-call-pair.md

## Goal

The admitting import statement appears inside the call-pair dropdown it
belongs to — at the top of the caller's section, where the statement
lives in the caller's file — and the detached panel-level "Imports
admitting these calls" section goes away.

## Acceptance criteria

- `renderCallPair` renders the pair's own `via_imports` entries
  (existing `renderImportEntry` markup: status chip + `renderCode`
  statement, module-name fallback intact) as the first content of the
  **caller's** `<section>` in the pair body, above the caller's code.
- Entries with `in_caller_code: true` (ticket 103) are not rendered —
  the statement is already visible inside the caller's code block.
- The panel-level admitting section and `dedupedViaImports` are removed
  from `showEdgeCalls`.
- The imports-edge panel (`showEdgeImports`) renders exactly as before.
- A pair with no `via_imports` (same-file call) renders exactly as
  before.

## Likely files

- `static/app.js` — `renderCallPair` gains the per-pair entries;
  `showEdgeCalls` drops the section; `dedupedViaImports` deleted.
- `static/style.css` — only if the entry needs spacing inside the
  section; reuse `.import-entry` styling otherwise.

## Out of scope

- Any Python change — ticket 103 lands first.
- Merging the statement lines into one continuous code block with the
  caller's code (ADR 039 alternative, deferred).
- JS test harness (standing rule: user eyeballs the UI).
