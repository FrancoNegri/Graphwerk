# 145. "Changed methods" code display mode

Status: done
Decision: docs/decisions/051-changed-methods-code-display-mode.md

## Goal

Add a third code-panel display mode, "changed methods," between the
existing "code + changes" and "changes only" radio options, that shows only
the changed method/function bodies (each in full context) of the selected
file or class node, instead of the whole container or bare diff lines.

## Acceptance criteria

- `#code-mode-toggle` in `static/index.html` has three radios in order:
  "code + changes" (`full`) → "changed methods" (`changed-methods`) →
  "changes only" (`changes-only`).
- Selecting a file or class node with `changed-methods` active renders, for
  each changed leaf descendant symbol (kind `function` or `method`, status
  in modified/added/deleted — i.e. not `unchanged`), that symbol's own
  already-computed `code` view (full context, same lines `full` mode would
  show if that symbol's node were selected directly), each under a heading
  identifying the symbol (e.g. its label/qualname).
- A container with a changed method nested inside a changed class only
  shows the method's own view, not the whole class body — i.e. selection of
  leaf changed symbols must not also pull in their ancestor class/file
  symbol's full-body view.
- Selecting a node that is itself a leaf (`function`/`method`) with
  `changed-methods` active renders identically to `full` mode for that
  node.
- Selecting a container node with no changed leaf descendants (e.g. nothing
  changed, or the only change is class-level code outside any method) with
  `changed-methods` active renders identically to `full` mode for that
  node.
- Switching modes while a node is already selected re-renders immediately
  (matches existing `full`/`changes-only` toggle behavior).
- No changes to any file outside `static/`.

## Likely files

- `static/index.html` — add the third radio to `#code-mode-toggle`.
- `static/app.js` — extend `codeDisplayMode` handling: a function that,
  given the selected node, walks `graphData` for descendant symbol nodes
  (via `parent`) to collect changed leaf (function/method) symbols, and a
  render path that stacks their individual `code` views with per-symbol
  headings instead of calling `codeModeLines`/`renderCode` on the
  container's own `code`.
- `static/style.css` — minor styling for the per-symbol heading, if needed.

## Out of scope

- Any backend/model change (`graphwerk/codeview.py`, `graphwerk/models.py`,
  `graphwerk/service.py`) — see ADR 051, no hunk-to-symbol mapping.
- Surfacing class-level-only changes (no changed method child) in this mode.
- Changing the separate `#changed-only` graph-visibility checkbox.
