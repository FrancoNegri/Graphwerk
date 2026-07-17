---
name: audit-tests
description: Use to work through the missing-test backlog the `audit` skill queued in docs/audit/README.md — "implement the missing tests", "close the test gaps", "work through the audit backlog", or "pick up finding F-014". Reads the findings ledger for category=missing-test, status=open, and writes one real test per finding via the same TDD discipline the `ticket` skill uses, in the module's existing style. If a new test reveals genuinely broken behavior rather than just an untested-but-correct path, it does NOT fix the code inline — it xfails the test, converts the ledger entry to a bug, and files a docs/tickets/NNN ticket, then moves on. Does not invent new findings and does not run the `audit` skill's doc/code sweep itself — it only consumes what's already queued.
---

# Audit Tests

`audit` finds where the test suite has a real gap and stops there on
purpose — this skill is the other half, closing gaps one at a time without
also re-deciding what counts as a gap. It never edits `graphwerk/*.py` to
add a feature or fix a bug; the only production code it may touch is the
narrow case in step 3 where a test it just wrote exposes broken behavior,
and even then it doesn't fix it — it documents and hands off, same as
`audit` would.

## 0. Load the queue

Read `docs/audit/README.md`. Filter the ledger to rows with
`Category: missing-test` and `Status: open`. If the user named a specific
finding (`F-014`), work that one; otherwise work the full queue, in ledger
order (oldest `First seen` first — earlier findings tend to be smaller and
more isolated, same reasoning `ticket`'s "smallest diff" bias uses).

If the queue is empty, say so and stop — don't go looking for new gaps
yourself, that's `audit`'s job, run separately so the two passes stay
decoupled.

For each finding, read its full entry in the run report it was recorded in
(`docs/audit/runs/NNN-*.md`, linked from the ledger row) — the ledger row
alone is a one-line summary; the run report has the actual evidence
(module/function, the specific uncovered input or branch) you need to
write the right test.

## 1. Match the module's existing test style before writing anything

Open the test file that already covers the module (or the nearest sibling
if none exists yet, e.g. `tests/staging/test_differ.py` for
`graphwerk/staging/differ.py`). Match its conventions: real fixtures over
mocks (actual small `.py` source strings, real `tmp_path` directories —
this codebase already commits to that, per `ticket`'s step 3), naming
pattern, and level of granularity (one scenario per test, not a
parametrized sweep unless the file already does that).

## 2. TDD, one finding at a time

For each queued finding:

1. **Write the test** that exercises exactly the edge case in the
   finding's Evidence — no more. Run it.
2. **If it passes immediately** — the behavior was already correct, just
   unexercised. This is the expected outcome for a true "missing test"
   finding:
   - Keep the test, run the full suite (a regression here is worth
     catching now).
   - Update the ledger row: `Status` → `resolved`, `Ticket / Test` column
     → the new test's path and name.
   - Append a short line to that finding's section noting resolution — do
     this by adding to the *next* run's report if `audit` is running
     again soon, or directly as a dated addendum under the finding's
     existing entry in its run report if not. Either way, the ledger row
     is the source of truth; keep it current.
3. **If it fails** — the finding undersold itself: this isn't a coverage
   gap, it's a live bug. Do not "fix" the code to make the test pass —
   that's `ticket`'s job, and doing it here would mean shipping a
   production change with no ADR/ticket trail and no acceptance criteria
   to check it against. Instead:
   - Mark the test `@pytest.mark.xfail(reason="graphwerk/tickets/NNN-...", strict=True)`
     so the suite stays green but the gap stays visible and executable —
     the moment the ticket lands, the test starts passing and `strict=True`
     turns that into a loud failure demanding the xfail marker be removed.
   - Update the finding's ledger row: `Category` → `bug`, `Status` →
     `ticketed`.
   - File `docs/tickets/NNN-<slug>.md` using the same template `audit`
     uses for bugs (`Decision:` pointing at the audit run report, plus a
     note that the regression test already exists at
     `tests/.../test_x.py::test_y` under an `xfail` marker — the ticket's
     acceptance criteria should include "remove the `xfail` marker and
     confirm it passes"). Add the row to `docs/tickets/README.md`.
4. **Suite** — run the full test suite before moving to the next finding
   in the queue, same as `ticket`'s per-criterion discipline.

## 3. Design bar

Same bar `ticket` step 4 sets for any test you write: descriptive test
names that state the scenario, no speculative coverage beyond the specific
finding, no comments explaining what the test does (the name and
assertions should already say that).

## 4. Close out

Summarize: how many findings were resolved (with test names), how many
turned out to be real bugs and got ticketed (with links), confirm the full
suite is green (including any new `xfail`s passing as expected-fail, not
erroring). If the queue had more findings than you worked through in this
pass, say which remain open so the next invocation picks up where this one
left off.
