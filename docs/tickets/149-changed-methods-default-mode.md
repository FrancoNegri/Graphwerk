# 149. "Changed methods" is the default code-view mode

Status: done
Decision: docs/decisions/053-changed-methods-default-code-view.md

## Goal

Make `changed-methods` the code panel's starting mode instead of `full`,
so opening a node with changed leaf descendants lands directly on the
narrowed view ticket 145 built.

## Acceptance criteria

- `static/index.html`'s `#code-mode-toggle`: the `checked` attribute moves
  from the `full` radio to the `changed-methods` radio (order of the three
  radios is unchanged).
- `static/app.js`: `codeDisplayMode` initializes to `"changed-methods"`.
- Selecting any node on first load (no prior toggle interaction) renders
  using `changed-methods` mode's rules — including its existing fallback
  to `full`-equivalent rendering for leaf nodes and containers with no
  changed leaf descendants (ticket 145, unchanged).
- Switching to `full` or `changes-only` and back still behaves exactly as
  today (this ticket only changes the initial/default value).

## Likely files

- `static/index.html` — move `checked`.
- `static/app.js` — `codeDisplayMode` initial value.

## Out of scope

- The `affected`-status leak into `changed-methods` mode — ticket 146,
  already scoped separately; land 146 first or alongside, since flipping
  the default makes that bug visible on every default node selection
  instead of only when a reviewer opts into the mode.
