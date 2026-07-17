---
name: audit
description: Run a full-repo consistency sweep of graphwerk — "audit the repo", "check for drift", "find bugs and gaps", "is the code still consistent with the docs", or any periodic health check that isn't about a single diff. Re-reads docs/02-04 and CLAUDE.md's invariants, re-reads its own findings ledger at docs/audit/README.md, then walks graphwerk/, static/, and tests/ layer by layer for three things: doc/code inconsistencies, bugs, and missing test coverage of realistic edge cases. Documents every finding in the ledger and a dated run report under docs/audit/runs/, and files a docs/tickets/NNN ticket (the same format the `ticket` skill consumes) for every open bug or inconsistency. Missing-test findings are NOT ticketed — they stay queued for the `audit-tests` skill. Does not touch graphwerk/*.py or static/* itself; like `north-star`, it stops at documentation. Not a substitute for `code-review` (diff-scoped) or `verify` (single-change-scoped) — this is whole-repo and stateful across runs.
---

# Audit

Design decisions get made deliberately (`north-star`) and implemented
carefully (`ticket`), but nothing currently re-checks, on a regular
cadence, whether the result still matches what was decided, or whether the
test suite actually covers what the code does. This skill is that
check: a full, repeatable sweep that reads the same docs, in the same
order, every time, and keeps a persistent record so findings don't get
re-discovered from scratch or silently dropped between runs.

This skill **documents, it does not fix**. It writes to `docs/audit/` and
`docs/tickets/` only. If you find yourself about to edit `graphwerk/*.py`,
`static/*`, or a test file, stop — that's a ticket for the `ticket` skill,
or a job for the `audit-tests` skill if it's a missing-test finding.

## 0. Re-read the design docs

Same set `north-star` reads, for the same reason — findings are judged
against what the project actually decided, not against instinct:

- `docs/02-product-concept.md` — what the graph is for (structural context,
  blast radius, change-dependency edges, per-node rationale, targeted
  re-prompting). A "bug" that's actually a feature the concept doc never
  promised isn't a finding.
- `docs/03-architecture-notes.md` — the hard problems already solved and the
  trap already avoided.
- `docs/04-roadmap.md` — current phase and its exit criterion, and what's
  explicitly "not now." Don't flag a "missing" Phase 4/5 feature as an
  inconsistency — that's the roadmap working as intended.
- `CLAUDE.md`, **Architecture invariants** — the concrete, checkable rules:
  real filesystem/worktree for the agent, symbol-qualified-name diffing
  (no hunk-to-symbol mapping), `FileIndex`/`SymbolInfo` as the
  language-neutral contract, Python-everywhere-JS-only-in-`static/`,
  minimal backend deps.
- `docs/decisions/README.md` and every ADR with status `proposed` or
  `accepted` — a decision the code doesn't yet reflect is either unfinished
  work (check `docs/tickets/README.md` for an open ticket already covering
  it — not a new finding) or drift (a finding).
- `docs/tickets/README.md` — know what's already `ready`/`in progress` so
  you don't file a duplicate ticket for something already tracked.

## 1. Re-read the ledger before looking at code

Read `docs/audit/README.md` in full. If it or `docs/audit/runs/` doesn't
exist yet, bootstrap it now (empty ledger table, empty runs table — see the
template already checked into `docs/audit/README.md`; create `runs/` when
writing the first run file). This is the "own state" step: know every
finding's current ID, category, and status before generating anything new,
so this run extends the ledger instead of restating it.

If the ledger has open findings from a previous run, re-verify each one
against the current code **before** hunting for anything new:

- Still present, unchanged → stays `open`.
- Fixed (a ticket closed it, or it was fixed incidentally) → mark
  `resolved`, note which commit/ticket in the run report.
- A bug/inconsistency ticket was filed but the ticket is `done` and the
  finding still reproduces → the fix didn't actually land; reopen loudly,
  don't file a second ticket silently.

## 2. Sweep the code, layer by layer

Full sweep every run — this is a small, fast-moving codebase (~5k lines);
incremental/diff-only scans would make findings depend on which commit you
last happened to run from, which breaks the determinism this skill exists
to provide. Use `git log` since the last run only to help *prioritize*
where to look first, never to skip a layer entirely.

Walk the same layers `ticket`'s step 2 defines boundaries for —
`models.py`, `indexing/`, `staging/`, `rationale/`, `apply.py`,
`service.py`, `server.py`/`cli.py`, `static/` — and for each, check three
things:

**a. Inconsistency** — does the code match what the docs above say it
does? Concretely: layer boundaries respected (no layer reaching into
another's internals), no new runtime dependency beyond fastapi/uvicorn in
`pyproject.toml`, no JS logic leaking outside `static/`, the differ still
comparing by qualified name with no hunk-to-symbol mapping creeping in,
`FileIndex`/`SymbolInfo` still the only contract new extractors implement.
If you find code that clearly **contradicts a standing invariant** (not
just a stale comment) — stop ticketing it as a small fix. That's the same
kind of change `north-star`'s step 3 gates: flag it distinctly in the run
report as "invariant-level — needs `north-star`, not a ticket" and say so
in the summary, rather than routing it into a two-line ticket that quietly
re-litigates the invariant. For smaller drift (a doc describing behavior
the code no longer has, or vice versa), note which side is actually wrong
— sometimes the fix is updating the doc, not the code — and say so in the
ticket's "Likely files."

**b. Bugs** — logic errors, unhandled realistic inputs, incorrect output.
Trace real inputs through the function, not just the happy path already
covered by tests. This codebase's own history is a good guide to the bug
shapes worth hunting for: malformed/unparseable staged files, non-Python
files, symlinks, `.gitignore`d paths, empty files, renamed/relocated
symbols, deleted files with dangling rationale, concurrent apply/reject
against a moving worktree. A finding needs a concrete failure scenario
(what input, what happens, why it's wrong) — "this could theoretically
fail" without a scenario isn't a finding, it's speculation.

**c. Missing test coverage** — for each function/branch, check whether
`tests/` covers the realistic edge cases, "within reason." Calibrate
"within reason" against the test suite's own existing style (real
fixtures, real temp directories, one clear scenario per test, no mocking
the filesystem, no combinatorial blow-up) rather than chasing branch-
coverage percentages — a gap is worth flagging when a plausible input
would hit un-exercised code, not because some line is technically
uncovered. Skip anything already listed as a known limitation in an ADR's
"Out of scope"/"Consequences" section — that's a documented tradeoff, not
a gap.

## 3. Record findings

For every new finding, append a row to the ledger table in
`docs/audit/README.md` with the next `F-NNN` ID (global counter, never
reused — check the highest existing ID across *all* statuses, not just
open ones) and write the detail into a new
`docs/audit/runs/NNN-<YYYY-MM-DD>.md` (own numbering, sequential, check
the Runs table for the next number):

```markdown
# Audit run NNN — <YYYY-MM-DD>

Commit: <git rev-parse --short HEAD>
Docs re-read: 02, 03, 04, CLAUDE.md, decisions/README (+ proposed/accepted
ADRs), tickets/README

## Findings this run

### F-NNN — <inconsistency|bug|missing-test> — open
**Location:** <path:line or module::function>
**Evidence:** <what you observed and why it's wrong, with a concrete
scenario for bugs, or the specific uncovered input/branch for missing-test>
**Ticket:** <docs/tickets/NNN-slug.md, or "queued for audit-tests" for
missing-test findings, or "escalate to north-star" for invariant-level
inconsistencies>

## Findings re-verified from prior runs
- F-NNN — still open (unchanged) / resolved (<how>) / reopened (<why>)

## Summary
<N> new findings (<a> inconsistency, <b> bug, <c> missing-test). <M>
tickets filed. <R> resolved since last run.
```

Update the ledger's Runs table with this run's counts, and update every
touched finding row's `Status` and `Ticket / Test` column in place.

## 4. File tickets for bugs and inconsistencies

For every `open` finding in category `bug` or `inconsistency` (excluding
anything you flagged as invariant-level in step 2a — escalate those to the
user instead), check `docs/tickets/README.md` for an existing open ticket
covering it first. If none exists, create
`docs/tickets/NNN-<slug>.md` using the exact template `north-star` uses,
with one deliberate substitution: no ADR exists for a bug, so `Decision:`
points at this run's report instead, which carries the "why":

```markdown
# NNN. <Title>

Status: ready
Decision: docs/audit/runs/MMM-<date>.md

## Goal
<what becomes true that wasn't — matches the finding's Evidence>

## Acceptance criteria
- <testable statement, including the regression test for the bug itself>

## Likely files
- <path> — <what changes; say explicitly if the doc, not the code, is what's wrong>

## Out of scope
<anything adjacent — don't let a bug ticket grow into a refactor>
```

Add a row to `docs/tickets/README.md`, same as any other ticket. Set the
ledger row's `Status` to `ticketed` and fill in the ticket link.

## 5. Leave missing-test findings queued

Do not ticket `missing-test` findings — they don't need a design decision
or a `ticket`-skill implementation pass, just a test. Leave their ledger
`Status` as `open`; the `audit-tests` skill reads exactly that queue. Do
not write the tests yourself here — that mixes this skill's "look and
record" pass with the other skill's "write and verify" pass, the same
separation `north-star`/`ticket` already rely on.

## 6. Close out

Summarize for the user: total findings this run by category, how many
were newly opened vs. re-verified, how many tickets were filed (with
links), how many missing-test findings are now queued, and whether
anything was escalated as invariant-level. Point at `docs/audit/runs/NNN-*.md`
for the full detail rather than repeating it all in chat. If findings were
escalated, say so plainly and stop — don't proceed to file a ticket for
something that actually needs a `north-star` pass.
