# 146. "Changed methods" mode excludes `affected` (unchanged-but-calling) leaves

Status: done
Decision: docs/decisions/051-changed-methods-code-display-mode.md

## Goal

Fix `changedLeafDescendants` so it matches ticket 145's own acceptance
criteria — only leaf symbols with status `modified`/`added`/`deleted`
count as "changed," never `affected` (unchanged itself, but calls into
changed code — `graphwerk/models.py:14`).

## Acceptance criteria

- `changedLeafDescendants` (`static/app.js`) includes a leaf
  (`function`/`method`) descendant only when its status is one of
  `modified`, `added`, `deleted` — not `unchanged` and not `affected`.
- Confirmed against live dogfood data: `TestAdapterResets._call` in the
  agendabot dogfood graph (status `affected`) must NOT appear when
  `changed-methods` mode is active and `TestAdapterResets` (or its parent
  file) is selected, while its sibling methods with genuinely
  modified/added/deleted status still do.
- Existing ticket 145 acceptance criteria (leaf-only, container fallback
  to `full` when no qualifying leaf exists, leaf-node identity with
  `full`) continue to hold — this is a narrowing of the status filter,
  not a change to the walk/fallback logic.

## Likely files

- `static/app.js` — `changedLeafDescendants`'s status check; introduce an
  explicit set (e.g. `{"modified", "added", "deleted"}`) mirroring the
  Python-side `CHANGED` set in `graphwerk/service.py:18`, instead of
  `n.status !== "unchanged"`. No JS test harness exists in this repo
  (static/ has no automated tests today); verify against the live
  agendabot dogfood graph's `TestAdapterResets` node per the acceptance
  criteria above.

## Out of scope

- The default-mode flip (ticket 149) — orthogonal.
- The admitting-import attribution bug (tickets 147/148) — separate
  panel, separate root cause.
