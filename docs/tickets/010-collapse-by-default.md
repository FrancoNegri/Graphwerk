# 010. Collapse unchanged files by default

Status: done
Decision: docs/decisions/002-graph-layout-legibility.md

## Goal

Big graphs open readable: files with nothing to review start as uniform
collapsed chips; changed and blast-radius files start expanded.

## Acceptance criteria

- On first load, a file whose strongest descendant status is `unchanged`
  renders collapsed; a file containing `modified`/`added`/`deleted`/
  `affected` symbols renders expanded.
- Double-click still toggles any file, and a manual toggle wins over the
  default for that file across poll-driven refreshes (`/api/hash` refetch).
- Collapsed chips render at a uniform size (fixed width, ellipsized label
  if needed) instead of label-width, so unchanged files read as a grid of
  same-sized tiles.
- A file that becomes changed on refresh (agent edits it mid-session)
  expands automatically unless the user manually collapsed it.
- Existing collapse behavior is preserved: strongest-child status color,
  no dangling edges (reroute to the file chip).

## Likely files

- `static/app.js` — default-collapse policy layered under the manual
  `collapsedFileIds` override; chip sizing style.

## Out of scope

Layer computation and banded placement (tickets 011, 012); persisting
state across page reloads.
