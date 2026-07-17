---
name: ticket
description: Use to implement one scoped graphwerk ticket end-to-end (docs/tickets/NNN-*.md), or any other small, well-defined change to the graphwerk codebase — "implement ticket 3", "let's build the hunk-level apply", "add a test for the differ and fix it". Enforces strict TDD, the smallest diff that satisfies the acceptance criteria, minimum coupling between the existing layers (models/indexing/staging/rationale/apply/service/server/static), high cohesion, small single-responsibility classes/functions, descriptive names, and a passing test for everything touched. If no ticket exists yet for a request this size, say so and suggest the `north-star` skill first instead of improvising scope.
---

# Ticket

Implements exactly **one** scoped ticket at a time, the same way regardless
of who wrote the ticket or how big the codebase gets: red, green, and no
bigger a diff than the acceptance criteria require.

## 0. Get a ticket, don't invent one

- If given a ticket path or number, read `docs/tickets/NNN-*.md` in full,
  then follow its `Decision:` link and read that ADR too — implementing
  from the ticket alone, without the "why," leads to technically-correct
  code that misses the point.
- If asked to do something ticket-shaped but no ticket exists: check
  `docs/tickets/README.md` for an open one first. If genuinely nothing
  fits, and the change is small and uncontroversial (a bug fix, a missing
  test, a one-line correction), proceed directly — writing a whole ADR for
  a two-line fix would be its own kind of waste. If the change is actually
  a design decision in disguise (new layer, new invariant, multi-file
  restructuring), stop and suggest `north-star` instead of freelancing it
  here.
- If the acceptance criteria are ambiguous or under-specified, ask rather
  than guess at scope. Guessing wrong here is expensive precisely because
  the rest of this skill is optimized for building the *right* small thing
  fast.

## 1. No test suite yet — bootstrap it the first time

Graphwerk currently has zero automated tests. The first ticket that touches
any Python logic should set up `pytest` as a **dev-only** dependency (it
does not belong in `pyproject.toml`'s runtime `dependencies`, per CLAUDE.md's
"backend deps stay minimal" — add it under
`[project.optional-dependencies] dev = ["pytest"]`), plus a `tests/` directory
mirroring the package layout (`tests/staging/test_differ.py` for
`graphwerk/staging/differ.py`, etc.). Do this once, as part of whichever
ticket needs it first — don't make it its own ticket.

## 2. Plan the smallest diff

Before writing anything, name the exact files you expect to touch and why.
Cross-check against the ticket's "Likely files" — if your plan reaches
further than that, that's a signal either the ticket was under-scoped (flag
it) or you're about to do more than asked (pull back).

Respect the existing layer boundaries — don't reach across them just
because it's convenient:

- `models.py` — pure data, no behavior beyond `to_dict()`
- `indexing/` — parses source into `FileIndex`/`SymbolInfo`; knows nothing
  about diffing or the graph
- `staging/` — diffs two trees; knows nothing about rationale or the API
- `rationale/` — sidecar + transcript mining; knows nothing about diffing
- `apply.py` — file writes/reject payloads; knows nothing about indexing
- `service.py` — the only layer allowed to know about all the others; it
  orchestrates, the others don't reach back into it
- `server.py`/`cli.py` — entry points; thin, no business logic of their own
- `static/` — the only JS in the project; no Node-side logic

A ticket whose natural implementation crosses these boundaries in a new way
is exactly the kind of thing that should have been caught by `north-star`
as an architecture decision — flag it rather than quietly wiring a new
cross-layer dependency.

## 3. TDD, one acceptance criterion at a time

For each acceptance criterion, in order:

1. **Red** — write the test that captures it, using real fixtures over
   mocks where reasonable (e.g. actual small `.py` source strings for the
   indexer/differ, real temp directories for staging/apply — this codebase
   is small and fast enough that faking the filesystem rarely earns its
   keep). Run it. Confirm it fails, and that it fails for the reason you
   expect, not by accident (import error, typo, etc.).
2. **Green** — write the minimum production code to pass it. Resist adding
   anything the current criterion doesn't need yet, even if you can see it
   coming — a later ticket can add it when it's actually needed.
3. **Refactor** — with the test green, clean up only what you just touched:
   split anything doing more than one job, name things for what they mean
   rather than what type they are, remove duplication you just introduced.
   Re-run the test after.
4. **Suite** — run the full test suite before moving to the next criterion.
   A regression caught here is cheap; caught later it's a mystery.

## 4. Design bar for anything you write or touch

- **Small, single-responsibility classes/functions.** If describing what a
  function does needs "and," split it.
- **High cohesion.** Data and the behavior that operates on it stay
  together; don't scatter related logic across layers to avoid touching a
  file.
- **Minimum coupling.** Depend on the layer boundary's existing contract
  (`FileIndex`, `SymbolInfo`, `GraphNode`, `Status`), not on another layer's
  internals.
- **Descriptive names.** A reader should get the intent from the name alone,
  without opening the function. No single-letter names outside short,
  obvious loop variables; no abbreviations that need decoding.
- **No speculative generality.** Build for the acceptance criteria in front
  of you, not for a hypothetical future one. Three similar lines beat a
  premature abstraction.
- **No comments explaining what** — only ones explaining a non-obvious why
  (matches the project-wide default; see CLAUDE.md).

## 5. Verify, don't just test

For anything touching `server.py`, `cli.py`, or the API surface, unit tests
aren't sufficient proof — CLAUDE.md is explicit that this project verifies
by curling the running API (`/api/graph`, `/api/hash`, `/api/apply`,
`/api/reject`), not just imports. Use the `verify` skill for this, or by
hand: run `graphwerk demo`, exercise the change, reset the demo afterward.

Do not attempt to check `static/` changes in a browser yourself — the user
verifies the frontend by hand (it's meant to stay thin per CLAUDE.md, so
there's little for a headless check to catch anyway). Land the JS change,
call out what you touched, and let them eyeball it.

## 6. Reset the dogfood server

The user usually keeps a graphwerk server running against a real repo pair
(the dogfood setup) while tickets land. After your changes it is still
running the *old* code — reset it at the end of every ticket, the same way
every time:

1. Find the running server and capture its exact command line:
   `pgrep -af 'graphwerk (demo|serve|start)'`.
2. If nothing is running, there is nothing to reset — say so and move on.
   Don't start a server the user didn't have running.
3. Kill it: `pkill -f 'graphwerk (demo|serve|start)'`.
4. Relaunch the captured command line **verbatim**, in the background —
   same subcommand, same `--base`/`--staged` pair, same `--host`/`--port`.
   Don't substitute the demo for the user's real pair, and don't drop
   `--host 0.0.0.0` if it was there (the user browses from another LAN
   device).
5. Confirm it's back up: `curl -s localhost:<port>/api/hash` returns a
   hash.

Do this after the full suite is green and after any demo workspace used in
step 5 has been reset — it's the last action before close-out, so the
user's browser is always one refresh away from the code you just landed.

## 7. Close it out

- Update the ticket's `Status:` to `done` (or `blocked: <why>` if you
  stopped short — don't silently leave it looking finished when it isn't).
- Summarize: what changed, what tests were added, and confirm the full
  suite is green.
- Commit the ticket's changes now, as its own commit — include the ticket
  file's `Status:` update in it. Don't bundle multiple tickets into one
  commit and don't leave a completed ticket uncommitted for a later batch.
- If you noticed the ticket was actually two things, or the ADR's scope
  didn't quite match reality, say so — that feedback belongs back in
  `docs/decisions/` or `docs/tickets/`, not silently absorbed.
