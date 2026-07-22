# 190. Frontend: `changed-methods` mode renders each method's `used_imports` block

Status: done
Decision: docs/decisions/064-changed-method-code-view-surfaces-its-imports.md

## Goal

A reviewer looking at a changed method in `changed-methods` code-display
mode (ADR 051, the default per ADR 053) sees the real import statement(s)
for any outside-scope name that method's body depends on, without leaving
that method's block.

## Acceptance criteria

- `renderChangedMethods` (`static/app.js`) renders `symbol.used_imports`
  (ticket 189's new payload field) for each changed leaf symbol, positioned
  above `renderCode(symbol.code)` (after the existing heading/Affects
  line).
- Visual treatment matches the calls panel's existing `import-entry`
  markup for admitting imports (`renderCallPair`) — one consistent look
  for "an import statement attached to a piece of code" across both
  panels, not a second bespoke style.
- A method with an empty/absent `used_imports` renders exactly as it does
  today (no empty block, no layout shift) — this is additive only for
  methods that actually have something to show.
- Manually verified against the agendabot dogfood repo (per CLAUDE.md's
  "verify by curling the API/using the UI, not just imports"): select
  `TestOnlyRouter` in `changed-methods` mode and confirm the `APIRouter`/
  `datetime`/`Any` bindings now render above `__init__`'s (and its nested
  `_slot_from_config`'s) code block.

## Likely files

- `static/app.js` — `renderChangedMethods`, reusing the existing
  import-entry rendering helper already used by `renderCallPair`.
- `static/style.css` (or wherever `.import-entry` is styled) — only if the
  existing class needs a shared rename/generalization to be reused outside
  the calls panel; no new visual language.

## Out of scope

- Any change to `renderCallPair`/the calls panel itself.
- `full`/`changes-only` mode rendering — unaffected (ADR 064: out of
  scope).
