---
name: north-star
description: Use before starting any nontrivial graphwerk feature or architectural change — "how should we build X", "let's design Y", "what's next on the roadmap", "should we change how the differ/apply/rationale works", or any request that would otherwise jump straight into multi-file code changes without first checking it against the product concept, the architecture invariants, and the current roadmap phase. Re-grounds the decision in docs/02-04 and CLAUDE.md, weighs real alternatives, writes a short ADR to docs/decisions/, and splits the decision into small ticket files under docs/tickets/ for the `ticket` skill to implement one at a time. Does NOT write implementation code — it stops at the plan, on purpose, so big decisions get made deliberately instead of accreting inside an unrelated coding session.
---

# North Star

Graphwerk moves in phases (`docs/04-roadmap.md`) built on top of a small set
of invariants (`CLAUDE.md`) that took real analysis to arrive at
(`docs/03-architecture-notes.md`). The fastest way to erode that is to let
each new feature get designed from scratch, in isolation, by whoever happens
to be implementing it that day. This skill is the checkpoint before that
happens: reorient in the existing thinking, make the decision explicitly,
write it down, then hand off small, independently implementable pieces to
the `ticket` skill.

This skill produces **plans and documents, not code**. If you find yourself
about to open an editor and change `graphwerk/*.py`, stop — that belongs in
a ticket, implemented via the `ticket` skill.

## 1. Re-read before deciding anything

Every time this skill runs — even if you (the assistant) recall these docs
from earlier in the conversation, re-read them, because the whole point is
to catch drift:

- `docs/02-product-concept.md` — the idea and what makes it more than a diff
  viewer (structural context, blast radius, change-dependency edges,
  per-node rationale, targeted re-prompting). Any new feature should serve
  one of these, or it's scope creep.
- `docs/03-architecture-notes.md` — the hard problems already analyzed
  (partial apply within a file, change interdependence) and the trap already
  avoided (intercepting agent writes). Don't re-litigate these from
  scratch; extend them.
- `docs/04-roadmap.md` — which phase is current, what its exit criterion is,
  and what's explicitly listed as "not now." A good idea that belongs in a
  later phase should be filed there, not pulled forward.
- `CLAUDE.md` — the standing rules, especially **Architecture invariants**:
  - the agent always gets a real filesystem (git worktree) — never
    intercept/absorb its writes
  - the differ compares symbols by qualified name across two parsed trees —
    no hunk-to-symbol mapping
  - `FileIndex`/`SymbolInfo` is the language-neutral contract — new
    languages are new extractors, not new models
  - Python everywhere, JS only in `static/`
  - backend deps stay minimal (fastapi + uvicorn only, stdlib otherwise)

## 2. Frame the decision

State in a couple of sentences:
- What problem this solves, and which part of the product concept it serves.
- Why now — does it match the current roadmap phase's goal, or is it a
  detour? If it's a detour, say so plainly and ask whether to proceed or
  defer it to the roadmap doc instead.

## 3. Check it against the invariants

Go through the invariants list above one by one and note whether this
decision is consistent with each. If it **conflicts with an existing
invariant** (e.g. it would need Node-side logic outside `static/`, add a new
backend dependency, add hunk-to-symbol mapping, or have the graph app absorb
writes instead of diffing a real worktree) — stop and ask the user before
going further. Invariants are prior user decisions; changing one is the
user's call, not something to decide silently mid-plan.

## 4. Weigh real alternatives

List at least two genuine options (not a straw-man vs. the obvious answer),
with the concrete tradeoff for each — what it costs in coupling, code, or
future flexibility, not just abstract pros/cons. Recommend one and say why,
but keep this section short: a table or three bullet points, not an essay.

## 5. Draw the scope line

Decide explicitly what's **in** for this decision and what's **out**
(deferred, or never). Prefer the smallest change that's still coherent —
matching how the roadmap itself is phased. "Out of scope" items that seem
worth doing later belong as a note in the ADR, not as scope creep now.

## 6. Write the ADR

Create `docs/decisions/NNN-<slug>.md` (zero-padded 3 digits, next number
after the highest existing one; check `docs/decisions/README.md`) using:

```markdown
# NNN. <Title>

Status: proposed
Date: <YYYY-MM-DD>

## Context
<the problem, tied back to docs/02's concept and docs/04's current phase>

## Decision
<what we're doing, in concrete terms>

## Alternatives considered
- <option> — <why not>
- <option> — <why not>

## Consequences
<what this makes easier, what it makes harder, any invariant it touches>

## Out of scope
<explicitly deferred items, and where they'd belong later (roadmap phase, etc.)>
```

Add a row to the table in `docs/decisions/README.md`.

## 7. Break it into tickets

Split the decision into the smallest set of independently implementable
tickets — each one small enough to finish in a single TDD sitting (typically
one class/function or one narrow vertical slice, touching one or two
files). Prefer more small tickets over fewer large ones; a ticket that
needs "and also refactor X" inside it is too big — split it.

For each, create `docs/tickets/NNN-<slug>.md` (own numbering, independent of
decisions) using:

```markdown
# NNN. <Title>

Status: ready
Decision: docs/decisions/MMM-<slug>.md

## Goal
<one or two sentences — what this ticket makes true that wasn't true before>

## Acceptance criteria
- <testable statement>
- <testable statement>

## Likely files
- <path> — <what changes>

## Out of scope
<anything adjacent that belongs in a different ticket>
```

Add a row to `docs/tickets/README.md` per ticket, linking back to the ADR.

## 8. Hand off

End by listing the ticket files created and telling the user they're ready
for the `ticket` skill, one at a time. Do not start implementing any of
them in this same pass — that mixes the deliberate, slower "which direction"
thinking with the fast, mechanical "make it so" work, which is exactly the
mixing this skill exists to prevent.
