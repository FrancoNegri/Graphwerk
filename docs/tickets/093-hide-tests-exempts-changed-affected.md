# 093. Hide-tests filter exempts changed and affected test nodes

Status: ready
Decision: docs/decisions/036-hide-tests-exempts-changed-and-affected.md

## Goal

With "hide tests" checked (the default), test nodes that are changed
(`modified`/`added`/`deleted`) or `affected` — directly or via a
descendant — stay visible; only signal-free test nodes are hidden.

## Acceptance criteria

- `toElements()` hides a node only when the payload's `is_test` is true
  **and** both its own status and its strongest-descendant status (the
  `strongestDescendantStatusByAncestor` map already computed for collapsed
  pills) are `unchanged`.
- A collapsed test file whose inner function is `affected` renders (with
  the affected pill color); an untouched test file does not.
- A test file the agent added or modified renders in the default view.
- `isTestPath` and its path-convention regexes are deleted from `app.js`;
  the payload flag is the only source.
- Verified by loading the demo (which stages a test-touching change or is
  temporarily given one) and eyeballing per the project's JS practice;
  no JS test harness is added.

## Likely files

- `static/app.js` — filter condition in `toElements`, delete `isTestPath`

## Out of scope

The server-side flag (ticket 092, prerequisite). The changed-only toggle.
Label or default-state changes to the checkbox.
