# 059. Collapsed containers surface deletions even when a stronger-ranked status wins

Status: proposed
Date: 2026-07-21

## Context

Dogfooding report (agendabot, today's run): `src/agendabot/webhook.py` was
split the same way ADR 029 already investigated once — most of its helpers
extracted into new files (`business.py`, `dependencies.py`, `turn.py`).
`get_calendar` moved to `dependencies.py`. The user's report: the graph
"does not show that it has been removed, it just silently drops it."

Reproduced directly against the real repo (`ChangeSetBuilder(agendabot,
ed0a077~1)`, `ed0a077` = the actual "Split webhook.py" commit):

- The differ is correct. `webhook.py`'s change set has 22 `deleted` symbols
  (including `get_calendar`), 1 `unchanged` (`health`), and 1 `modified`
  (`twilio_webhook` — its own body changed this time, not just a call
  target moving elsewhere). `service.py` and `server.py` pass all of this
  through untouched; `static/app.js` has a real `deleted` color (red,
  ADR 030) and a dashed/ghost border for it (ADR 029/ticket 078).
- The gap is `strongestDescendantStatusByAncestor`'s aggregation
  (`static/app.js`, `STATUS_RANK = ["modified", "added", "deleted",
  "affected", "unchanged"]`, first-match-wins). Because `twilio_webhook` is
  `modified`, the collapsed `webhook.py` pill's `collapsedStatus` resolves
  to `modified` — the same green a container with **zero** deletions gets.
  22 deleted symbols, including the reported `get_calendar`, contribute
  nothing to how the collapsed container looks. Expanding the file still
  shows every deleted child correctly (confirmed above) — the information
  isn't lost, only inaccessible from the collapsed view a big repo mostly
  lives in (Phase 2's collapse-by-default, ADR 015).

This is a different bug from ADR 029's, not a re-litigation of it. ADR 029
handled the case where deletion is the *only* signal among a container's
children (nothing modified/added) and fixed a rendering gap so `deleted`
reads distinctly once collapsed. It explicitly scoped out "any change to
how `collapsedStatus` is ranked/aggregated" as out of scope. Today's
report is exactly that ranking behavior, now visibly wrong: a *mix* of
`modified` and heavily-`deleted` children, where the higher-ranked status
fully masks the lower-ranked one instead of just winning the color.

Ties directly to docs/02's "blast radius for humans" pitch — the whole
point of the collapsed view is to tell a reviewer where to look. A
same-review AI refactor that guts 22 functions out of a file is exactly
the kind of thing blast radius exists to surface, and it's currently
invisible unless the reviewer thinks to expand every modified-looking
file "just in case." This is Phase 2 real-repo hardening
(docs/04-roadmap.md), not a detour.

## Decision

Add a second, independent signal to the collapse aggregation:
`hasDeletedDescendant` — true if *any* descendant symbol is `deleted`,
computed alongside (not instead of) the existing rank-based
`collapsedStatus`. `collapsedStatus` keeps deciding the container's fill/
border color exactly as today — no change to `STATUS_RANK` or what wins.

Extend the existing dashed-border/reduced-opacity "ghost" treatment
(ADR 029/030) to apply whenever `hasDeletedDescendant` is true, not only
when `collapsedStatus === 'deleted'`. A collapsed `webhook.py` in today's
scenario would render its normal `modified` green fill (correctly — that
*is* the dominant activity) with the ghost border layered on top (a
deletion happened in here too, regardless of what else did). This is a
CSS-selector/data-attribute change in `static/app.js` only — no backend
change, no new dependency, same view-logic-lives-in-JS split ADR 029
already used (ADR 013/014/015).

## Alternatives considered

- **Reorder `STATUS_RANK` to put `deleted` above `modified`/`added`.**
  One-line change, keeps a single-color model. Rejected: flips the same
  problem the other way — a file that mostly grew, with one helper deleted
  along the way, would render fully red/ghosted as if it were mostly
  gutted. ADR 029 already rejected the mirror-image version of this move
  (letting the file's own `modified` status override `collapsedStatus`)
  for the same reason: it flattens a distinction `collapsedStatus` exists
  to preserve.
- **Replace the single `collapsedStatus` color with a full breakdown**
  (counts per status, shown in a tooltip or badge — "22 deleted, 1
  modified"). More complete, but a bigger UI surface (tooltip/label work)
  than this report needs; the ghost-border cue already answers "should I
  expand this" without answering "by how much," which is enough for now.

## Consequences

- A collapsed file/class that lost symbols reads as "something got
  deleted in here" via the ghost border, no matter what else changed
  alongside it — closing exactly the gap the dogfood report hit.
- `collapsedStatus`'s color still means what it meant before (the
  strongest single kind of activity), so every other collapse shape
  (pure-added, pure-affected, etc.) is unaffected.
- Two independent visual signals (fill color + border style) on one node
  is a small increase in encoding density; acceptable since both already
  exist today, just newly decoupled.

## Out of scope

- **Symbol-move detection** (a deleted-here/added-there pair recognized as
  one relocation). Still the same gap ADR 029 deferred; unrelated to this
  fix and unresolved by it. File separately if a review session needs it.
- Any change to `STATUS_RANK`'s order or what determines the primary
  collapsed color.
- Per-status counts, tooltips, or badges beyond the ghost-border cue —
  future richness if the border alone proves insufficient in practice.
- Backend/differ/service changes — confirmed correct in this
  investigation, nothing to fix there.
