# 167. Collapsed containers ghost-border when they contain a deleted descendant

Status: done
Decision: docs/decisions/059-collapsed-container-deletion-visibility.md

## Goal

A collapsed file/class pill shows the dashed/ghost border whenever any of
its descendant symbols is `deleted`, even when another descendant's status
(`modified`/`added`) ranks higher and wins the pill's fill/border color.
Today the ghost border only appears when `collapsedStatus` itself resolves
to `deleted`, so a container with a mix of deleted and modified/added
children silently loses the deletion signal.

## Acceptance criteria

- `strongestDescendantStatusByAncestor` (or a sibling computation next to
  it) also produces, per ancestor id, whether any descendant symbol status
  is `deleted` — independent of which status wins the existing rank.
- That result is threaded onto the collapsed node's data the same way
  `collapsedStatus` already is, and drives a new selector/attribute so the
  existing ghost treatment (`border-style: dashed`, `opacity: 0.6`)
  applies whenever it's true, regardless of `collapsedStatus`'s value.
- `collapsedStatus` itself, `STATUS_RANK`, and the color each status
  produces are unchanged — this only adds the border cue, it doesn't
  change what wins the fill color.
- A container with zero deleted descendants renders exactly as it does
  today (no regression to the existing pure-`deleted`, pure-`modified`,
  pure-`added` etc. cases already covered by ADR 029/030).
- Verify against the live agendabot dogfood scenario (`webhook.py` split,
  `get_calendar` deleted alongside `twilio_webhook` modified): collapsed
  `webhook.py` shows its normal modified-green fill with the ghost border
  now layered on.

## Likely files

- `static/app.js` — `strongestDescendantStatusByAncestor` (or new sibling
  function), the `toElements`/node-data wiring that currently sets
  `collapsedStatus`, and the Cytoscape style selectors around
  `node[status='deleted'], node[collapsedStatus='deleted']`.

## Out of scope

- Symbol-move detection (ADR 029's deferred item; unrelated).
- Reordering `STATUS_RANK` or changing which status wins the fill color.
- Counts/tooltips/badges beyond the ghost-border cue.
