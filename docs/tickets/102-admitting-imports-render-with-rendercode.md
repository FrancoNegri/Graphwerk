# 102. Admitting-imports section renders the statement via `renderCode`

Status: done
Decision: docs/decisions/038-admitting-imports-render-as-real-statements.md

## Goal

The calls panel's "Imports admitting these calls" entries show the real,
syntax-highlighted import statement instead of the bare module name.

## Acceptance criteria

- `toElements` (`static/app.js`) carries each pair's `via_imports` entries
  through unchanged (the `code` field arrives with them; no new plumbing
  beyond what ticket 091 added).
- `renderImportEntry` renders the status chip plus, when the entry has a
  `code` field, the statement through the existing `renderCode` markup
  (same `.code` container the call pairs use); entries without `code` keep
  today's chip + module-name rendering — which also keeps the imports-edge
  panel (`showEdgeImports`, no `code` field) working unchanged.
- Dedupe in `dedupedViaImports` stays keyed on module+status.
- No new JS logic beyond the conditional render (ADR 005 / thin-JS rule).
- Verified by eyeballing the agendabot dogfood graph: the
  `webhook.py → deps.py` calls edge's panel shows
  `from agendabot.deps import get_classify_fn` highlighted, with an
  `added` chip and an add-gutter line.

## Likely files

- `static/app.js` — `renderImportEntry` conditional code render.
- `static/style.css` — only if the code block needs spacing inside
  `.import-entry`.

## Out of scope

- Backend fields — tickets 100/101 (this ticket depends on both landing
  first).
- Upgrading the imports-edge panel to code rendering (ADR 038, out of
  scope).
