# 036. Hide-tests exempts changed and affected tests

Status: proposed
Date: 2026-07-17

## Context

The "hide tests" toggle ships checked (`static/index.html`), and its filter
drops every node whose path looks like a test file — unconditionally. Two
kinds of review signal disappear with them:

- **Tests the agent changed.** A staged change that adds or modifies
  `tests/test_foo.py` is invisible in the default view; the reviewer can
  miss entire staged files unless they think to uncheck the toggle.
- **Tests in the blast radius.** "Blast radius for humans" is a core pillar
  of the concept (docs/02), and test functions are the most common affected
  callers of changed code. `_mark_affected` correctly marks them yellow —
  and then the default view hides them.

The toggle's original purpose (keep big graphs readable by dropping the
test-file noise) is right; its scope is wrong. Unchanged, unaffected tests
are noise. Changed or affected tests are exactly what the tool exists to
surface.

There is a second, smaller drift: the test-path convention is implemented
twice — `layout._is_test_path` (Python) and `isTestPath` (app.js) — which
ADR 005's thin-JS rule says shouldn't happen.

## Decision

The hide-tests filter only hides test nodes that carry no review signal:

- The server computes `is_test` per node (from the node's path, using the
  existing `layout._is_test_path` convention) and includes it in the
  snapshot payload.
- The JS filter hides a node only when `is_test` is true **and** the node's
  status — or, for containers, the strongest status among its descendants —
  is `unchanged`. Changed (`modified`/`added`/`deleted`) and `affected`
  test nodes stay visible with the toggle checked.
- `app.js` drops its local `isTestPath` and consumes the payload flag,
  closing the ADR 005 duplication.

The toggle's label and default stay as they are; its meaning tightens from
"hide all tests" to "hide tests that don't matter to this change".

## Alternatives considered

- **Uncheck hide-tests by default** — restores visibility but re-admits all
  the unchanged-test clutter the toggle was added to remove; worst of both.
- **Pure JS tweak (keep `isTestPath` client-side, add the status
  exemption)** — smallest diff, but leaves the test-path convention
  duplicated across Python and JS, against ADR 005 and the standing
  thin-JS rule. The server-side flag costs one payload field and deletes
  the duplicate.
- **Filter server-side entirely (server omits hideable tests)** — the
  toggle is client view state; moving it server-side would need a query
  parameter and a refetch per toggle flip, for no gain over filtering a
  payload the client already has.

## Consequences

- The default view shows every staged test change and every affected test —
  no more silent misses.
- One authoritative test-path convention, in Python, unit-testable.
- Payload grows by one boolean per test node (omitted when false).
- The JS filter must consult the strongest-descendant status it already
  computes for collapsed pills (`strongestDescendantStatusByAncestor`), so
  a collapsed test *file* whose inner function is affected stays visible.

## Out of scope

- Any change to the changed-only ("changed + blast radius only") toggle —
  it already includes affected test nodes once hide-tests stops eating them.
- Excluding test files from `_mark_affected` or edge building — untouched.
- Persisting toggle state across reloads — separate concern, not requested.
