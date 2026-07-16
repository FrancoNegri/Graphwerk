# 027. Rationale bullets must justify, not just describe

Status: proposed
Date: 2026-07-16

## Context

ADR 025/026 fixed *attribution* — the right text ends up on the right
node. Re-reading the actual text on the `webhook/` split session (the same
one ADR 026 was diagnosed against) shows a second, separate problem:
several bullets ignore `SESSION_GUIDANCE`'s own explicit instruction
("stating why that change serves the request, **not** what the code
does"):

| file | bullet reason | justifies the request, or just describes? |
|---|---|---|
| `deps.py` | "FastAPI dependency-injection providers." | describes |
| `context.py` | "builds `ConversationContext` from state/business/time." | describes |
| `rendering.py` | "templating/output-formatting concern." | describes |
| `state.py` | "conversation-state transition logic." | describes |
| `flags.py` | "shared env-derived flags, split out since several other modules need them." | justifies |
| `business.py` | "loading/DB-sync concern, isolated from caching and HTTP concerns." | borderline — names what it's isolated *from*, close to a reason |

The triggering request was "webhook.py has too many dependencies, could
you split it to get more granular classes with just one concern" — a
reviewer reading `deps.py`'s bullet learns what the module contains but
not why grouping those six functions together, specifically, satisfies
that request. [02-product-concept.md](../02-product-concept.md)'s pitch
depends on the rationale supporting "does the stated intent match what the
code does" — a bullet that only restates what the code does makes that
check circular for exactly the nodes where it matters (a module whose
existence itself needs justifying, not just its content).

This is a third consecutive dogfood finding on the rationale pipeline
(ADR 025 → 026 → this), each surfaced by re-checking the *same* live
session as it evolved rather than treating the first fix as done. Still
in-phase for the reason the first two were: Phase 2's exit criterion is
dogfooding real sessions, and each of these is a defect that only shows up
by doing that.

## Decision

Two changes, following the same layered pattern as ADR 025/026 (strengthen
what's asked for, then backstop with a cheap detector — don't rely on
either alone, since guidance-only fixes have already proven insufficient
twice in this investigation):

1. **Sharpen `SESSION_GUIDANCE`** with a contrastive example (a
   "describes" line vs. a "justifies" line for the same file), not just
   the current single positive example — the current wording states the
   rule but the agent doesn't reliably apply it to every bullet in a long
   list; showing the failure mode directly is more concrete than restating
   the rule.
2. **Flag purely-descriptive bullets with a cheap heuristic.** A reason
   with no causal/justifying connective (`because`, `since`, `so that`,
   `so it`, `in order to`, `to avoid`, `given that`, `which lets`, `which
   allows`) is very likely describing, not justifying. Surface this as a
   new node-level signal (e.g. `why_justifies: bool`), checked only when
   the rationale is otherwise confident (a real guidance bullet or mention
   — no point flagging content quality on text we already know is a weak
   proximity guess). Render it in the sidebar as a subdued nudge, same
   mechanism as ADR 025's confidence marker (tickets 068/069).

## Alternatives considered

- **Guidance-text change only.** Rejected for the same reason ADR 025 and
  026 both rejected it: this is the third time in one investigation that
  "ask the agent more clearly" hasn't been sufficient on its own once
  checked against a real session.
- **Post-hoc summarization/rewrite pass (Haiku)** — the mechanism
  `03-architecture-notes.md` and roadmap Phase 5 already earmark for
  rationale quality. Most robust (an LLM can actually judge "does this
  justify," a regex can't), but a real infrastructure step up: a new
  outbound model call per session, cost/latency, and a decision about when
  to trigger it (`/api/hash` currently polls every 1.5s — running this on
  every poll would be wasteful, same shape of problem ADR 019 already
  fixed for snapshot recompute). Roadmap Phase 5 already flagged rationale
  quality as pulled-forward-if-needed once before (ticket 007) — if the
  cheap heuristic here proves insufficient on the next dogfood check,
  that's the trigger to pull this forward for real, not now.
- **Suppress bullets that fail the heuristic instead of marking them.**
  Throws away real information — a purely descriptive bullet is still
  more useful than nothing, especially since its *attribution* is
  correct. Marking-not-suppressing is the same choice ADR 025 already made
  for low-confidence text, for the same reason.

## Consequences

- Reviewers get a second, independent signal from the existing confidence
  marker: "this is attributed to the right node" (ADR 025) vs. "this
  actually argues for the change" (this ADR) — a bullet can be confident
  and still non-justifying, and the UI should be able to say so.
- No backend dependency added; stdlib regex only, consistent with "backend
  deps stay minimal."
- Touches `graphwerk/rationale/guidance.py`, `graphwerk/rationale/attribution.py`,
  `graphwerk/rationale/miner.py`, `graphwerk/models.py`, `graphwerk/service.py`,
  `static/app.js` (thin consumption only).
- The heuristic is a nudge, not a judgment — explicitly acknowledged as
  imprecise (a well-written descriptive sentence can still be a good
  reason; a sentence with "because" in it can still be a weak one). This
  is consistent with the product's existing stance that rationale is
  review *assistance*, never verified truth.

## Out of scope

- The Haiku summarization/rewrite pass — stays a Phase 5 item unless the
  next dogfood check shows the heuristic isn't enough.
- Re-litigating `SESSION_GUIDANCE`'s overall structure (ADR 012) beyond
  adding the contrastive example.
- Tuning the connective word list beyond what's needed to pass the
  observed cases — expand only if dogfooding turns up more false
  negatives/positives.
