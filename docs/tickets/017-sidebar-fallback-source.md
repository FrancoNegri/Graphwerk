# 017. Sidebar: render source as fallback code view when a node has no diff

Status: ready
Decision: docs/decisions/004-always-show-source.md

## Goal

Clicking any node — file, class, or function — shows its code in the
sidebar, even when nothing changed, using ticket 016's new `source` field.

## Acceptance criteria

- `showDetails()` shows a new code section whenever `node.diff` is falsy
  and `node.source` is present, rendering `node.source` verbatim (reuse the
  existing `esc()` escaping used for diff/why text).
- The existing diff section's behavior for changed nodes is unchanged —
  diff stays the primary view when one exists; the new section and the diff
  section are mutually exclusive (never both visible for the same node).
- A node with neither `diff` nor `source` (shouldn't occur post-016) leaves
  both sections hidden, matching current behavior for that edge case.
- `static/index.html` gets the new section markup; `static/style.css` gets
  matching styling (reuse the `.diff`/`<pre>` styling already used for
  diffs, since it's a monospace code block either way).
- Verified in the running demo: click an unchanged function and confirm its
  code renders in the sidebar where previously nothing did; click a changed
  node and confirm the diff still renders as before.

## Likely files

- `static/app.js` — `showDetails()`.
- `static/index.html` — new section markup.
- `static/style.css` — styling.

## Out of scope

Syntax highlighting, line numbers; backend changes (ticket 016).
