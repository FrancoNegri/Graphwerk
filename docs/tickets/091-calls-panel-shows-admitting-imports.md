# 091. Calls panel shows the imports admitting its calls

Status: ready
Decision: docs/decisions/035-calls-panel-surfaces-admitting-imports.md

## Goal

Clicking a `calls` edge shows, under the collapsed call pairs, which
import(s) make those calls reachable — each with its status chip — so
the reviewer sees "added twilio_webhook → get_classify_fn, via the added
`agendabot.deps` import" in one panel.

## Acceptance criteria

- `toElements` (`static/app.js`) plumbs each underlying call edge's
  `via_imports` payload field into the aggregated edge's per-pair data
  (alongside the existing `source`/`target`/`status`/`module` push).
- `showEdgeCalls` renders a section below the call-pair list containing
  the union of the collapsed pairs' `via_imports`, deduped by
  module+status, reusing the existing `renderImportEntry` markup (status
  chip + module name). No section is rendered when no pair carries
  `via_imports` (e.g. all same-file calls).
- No new JS logic beyond dedupe-and-render of payload fields (ADR 005 /
  thin-JS rule); the imports-edge panel (`showEdgeImports`) is untouched.
- Verified by eyeballing the agendabot dogfood graph: the
  `webhook.py → deps.py` calls edge's panel lists the
  `agendabot.deps` import with an `added` chip under the
  `twilio_webhook → get_classify_fn` pair.

## Likely files

- `static/app.js` — `toElements` edge aggregation, `showEdgeCalls`.
- `static/index.html` — only if the panel needs a heading element rather
  than markup emitted from `showEdgeCalls`.

## Out of scope

- Backend field — ticket 090 (this ticket depends on it landing first).
- Changing the imports-view default toggle (ADR 035, Alternatives).
- Any change to the imports-edge click panel.
