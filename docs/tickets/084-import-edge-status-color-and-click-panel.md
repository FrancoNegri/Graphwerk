# 084. Import edges colored by status; clicking one lists the pertinent imports

Status: ready
Decision: docs/decisions/033-import-edge-status-and-pertinent-import-inspection.md

## Goal

The graph visually distinguishes a new/removed import edge from a
long-standing one, and clicking an `imports` edge shows exactly which
module(s) were added/removed for that file pair — without dumping the
whole file diff, which is already one click away via the file node itself.

## Acceptance criteria

- The `edge[kind='imports']` Cytoscape style (`static/app.js`) colors
  `line-color`/`target-arrow-color` from the same `COLORS[status]` map
  `calls` edges already use, keeping the dashed `line-style` that
  distinguishes imports from calls visually.
- The existing `edge[status='unchanged']` hover-reveal rule (ADR 020)
  continues to apply unchanged — no changes needed there, but confirm by
  test/manual check that a genuinely unchanged import edge stays
  hover-only while an added/removed one renders visible by default.
- A new tap handler, `cy.on("tap", "edge[kind='imports']", ...)`, opens a
  panel listing each fused sub-edge's module name and status (badge reusing
  the existing `.chip` classes), analogous to `showEdgeCalls`/
  `renderCallPair` but without the code sections — just "`+ module.name`" /
  "`- module.name`" per entry.
- Fused edge data (`buildElements` in `static/app.js`) carries `module`
  through the per-source-target array it already builds for `calls` edges,
  so the click panel has the data it needs without extra fetches.
- Manual check (per `verify` skill / CLAUDE.md UI-change guidance): stage a
  change that only touches an import (add one, remove one, leave one
  alone) in the demo tree, confirm the corresponding file-to-file edges
  render colored/visible for the changed imports, gray/hover-only for the
  unchanged one, and clicking a colored one shows the right module name and
  status.

## Likely files

- `static/app.js` — edge style rule, `buildElements` fusion, new tap
  handler + render function.
- `static/index.html` — new panel markup if not reusing `#edge-calls`/
  `#d-calls` directly (implementer's call which is cleaner).
- `static/style.css` — only if the reused/new panel needs adjustments
  beyond the existing `.chip` classes.

## Out of scope

- Any backend change — this ticket only consumes `status`/`module` already
  present on the payload after tickets 082/083.
- Extending blast-radius coloring to imports (ADR 033, "Out of scope").
