# 155. Sidebar: only the code section scrolls

Status: done
Decision: docs/decisions/057-sidebar-code-scroll-drop-reject-ui.md

## Goal

Scrolling a long code view no longer pushes the code-mode toggle, node
header/status, path, or why-section out of view — those stay put, and only
the code block scrolls.

## Acceptance criteria

- `#sidebar` itself no longer scrolls as a whole (drop its `overflow-y:
  auto`); it lays out as a column that fits the viewport height.
- With a node selected whose code overflows the available height, the
  code-mode toggle, `#d-label`/`.meta`/`.path`, and `#why-section` (when
  shown) remain visible without scrolling, while `#code-section`'s content
  scrolls vertically within its own box.
- `#edge-calls` (the separate calls/imports panel) gets the same treatment:
  its own long content scrolls in place without the panel's heading
  scrolling away, consistent with `#details`.
- No regression to existing horizontal scroll on individual `.code`/`.diff`
  blocks for long lines.

## Likely files

- `static/style.css` — `#sidebar` (currently `overflow-y: auto` at the
  aside level, style.css:216-222) becomes a non-scrolling flex column;
  `#details`/`#code-section` (or a wrapper around `#d-code`) gets `flex: 1;
  min-height: 0; overflow-y: auto` so it's the one growing/scrolling region.
  Apply the equivalent to `#edge-calls`/`#d-calls`.
- `static/index.html` — only if the flex restructuring needs an extra
  wrapper element around the scrollable region; no content changes expected.

## Out of scope

- Any change to what's rendered inside the code section (ticket 156 handles
  the actions-section content below it).
