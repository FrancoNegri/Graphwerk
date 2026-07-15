# 047. Generalize collapse to every container, always collapsed by default

Status: ready
Decision: docs/decisions/015-contract-by-default.md

## Goal

Every container node (file or class) starts collapsed regardless of
whether it needs review; a container stays open only if the user has
double-clicked it open. Class nodes gain the same collapse affordance and
chip styling files already have.

## Acceptance criteria

- `effectiveCollapsedFileIds` (rename to reflect the wider scope, e.g.
  `effectiveCollapsedContainerIds`) collapses every node that is some other
  node's `parent` (file or class) unless that id is in `userExpandedIds`.
  `fileNeedsReview` and the "needs review stays expanded" branch are
  removed; `userCollapsedFileIds` is removed as redundant (collapsed is
  now the default with no override needed to reach it).
- The dbltap-to-toggle listener fires for `node[kind='class']` as well as
  `node[kind='file']`; toggling a class behaves like toggling a file
  (collapses/expands, carries its `collapsedStatus` chip color).
- The `[collapsedStatus]` chip style (uniform size, status-colored
  background, centered label) applies to collapsed nodes of any kind, not
  just `kind='file']`.
- `representativeId`/edge routing in `toElements` continues to work
  unchanged in behavior for classes (it already walks any ancestor;
  confirm the container-id set it checks now includes class ids).
- Manual check: load the demo graph — every file and every class starts
  as a collapsed, status-colored chip, including files/classes that
  contain a modified or added symbol. Double-clicking a class chip expands
  it to show its methods; double-clicking again re-collapses it.

## Likely files

- `static/app.js` — `effectiveCollapsedFileIds`, `fileNeedsReview`,
  `userCollapsedFileIds`/`userExpandedFileIds`, `toggleFileCollapsed`, the
  dbltap listener, the `[collapsedStatus]` style selector.

## Out of scope

- Default value of `show-calls` (ticket 048).
- Method-level collapse — methods have no children.
- Edge status coloring / click-to-list (tickets 049-051).
