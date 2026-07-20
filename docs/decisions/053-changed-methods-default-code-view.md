# 053. "Changed methods" becomes the default code-view mode

Status: proposed
Date: 2026-07-20

## Context

Ticket 145 / ADR 051 added `changed-methods` as a third code-panel radio,
positioned between the two existing modes, specifically to solve the "one
changed method among several unchanged ones" case ADR 051 documented: `full`
buries the change, `changes-only` strips context. It shipped as an
additional option; the default stayed `full` (`static/index.html:50`,
`app.js:40`).

Continued dogfooding (this session, agendabot) confirms ADR 051's premise
in practice: selecting a file or class node defaults to the view that's
least useful for the common case (one or two changed methods in a larger
container), requiring an extra click every time to reach the view that
actually answers the reviewer's question. Phase 2's goal is dogfooding
graphwerk against real sessions until the review surface is actually
usable session over session (docs/04) — a default that fights the common
case works against that goal every time a node is opened.

## Decision

Make `changed-methods` the default code-view mode:

- `static/index.html`: move `checked` from the `full` radio to the
  `changed-methods` radio.
- `static/app.js`: `codeDisplayMode` initializes to `"changed-methods"`
  instead of `"full"`.

Fallback behavior is unchanged (ADR 051): a leaf node, or a container with
no changed leaf descendants, still renders identically to `full` mode — so
the only observable change is for containers that *do* have changed leaf
descendants, which is exactly the case this mode exists for.

## Alternatives considered

- **Keep `full` as default, rely on the reviewer to switch** — status quo;
  rejected per the dogfood evidence above, it's an extra click on the
  common path with no offsetting benefit (the fallback already covers the
  cases where `full` and `changed-methods` render identically).
- **Remember the last-used mode per session (localStorage or similar)** —
  more flexible, adapts to reviewer preference over time, but is a new
  piece of client-side state with its own edge cases (stale mode across
  page reloads/tabs, first-visit default still needs picking). Rejected
  for now: no evidence yet that reviewers want a *different* default than
  `changed-methods`, so the added state buys nothing today; revisit if
  dogfooding surfaces reviewers who prefer another mode as their default.

## Consequences

- Every fresh node selection with changed leaf descendants opens directly
  on the narrowed view; no backend or model change.
- Anyone relying on `full` as the landing view now takes one extra click
  the other way (to `full`) instead — a wash in click count, shifted
  toward the mode ADR 051 was built to make the common case.
- No invariant touched: pure client-side default change in `static/`.

## Out of scope

- Any change to `changed-methods` mode's own logic (see ticket 146 for the
  separate `affected`-status bug found in this same investigation) — this
  ADR only changes which mode starts selected.
- Per-session/remembered mode preference — see Alternatives.
