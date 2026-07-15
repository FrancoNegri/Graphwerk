# 027. Sidebar renders the unified code view

Status: done
Decision: docs/decisions/007-sidebar-code-view.md

Depends on: ticket 026.

## Goal

The sidebar's separate diff and source sections become one code view: the
node's entire source with line numbers, added/removed line backgrounds,
and token colors — for every selected node.

## Acceptance criteria

- `index.html`: the `diff-section` and `source-section` blocks are
  replaced by a single code section.
- `app.js`: renders `node.code` — per line: line number, `op` class on the
  row, span classes wrapped around the highlighted ranges, all text going
  through the existing `esc()`. No parsing, diffing, or tokenizing
  client-side; nodes with `code == null` show nothing (status chip and
  "why" still render).
- The reject payload still sends `node.diff` unchanged.
- `style.css`: token classes (`kw`, `def`, `str`, `com`, `num`) and
  add/del row backgrounds legible against the existing dark sidebar
  styling; context rows keep the plain background.
- Per the thin-JS rule there is no JS test harness — verification is
  eyeballing the running UI (demo tree: one modified, one added, one
  deleted, one unchanged node) plus the existing Python suite staying
  green.

## Likely files

- `static/index.html` — code section
- `static/app.js` — code renderer replacing `renderDiff`/source fill
- `static/style.css` — token + row styles

## Out of scope

Removing `source`/`diff` from the payload (ticket 028 handles `source`;
`diff` stays for reject); word-level emphasis; collapsing long unchanged
regions.
