# 057. Sidebar: code-only scroll region, drop the reject-comment UI

Status: proposed
Date: 2026-07-20

## Context

The review sidebar (`#sidebar`) currently scrolls as one block: the
code-mode toggle, node header/status chips, path, "why" section, code
section, and actions section all move together. Long code views push the
toggle and status out of view, which is the wrong tradeoff — those are
orientation, the code is what needs room to scroll.

Separately, `#actions` still renders a structured reject-comment box
(`#reject-box`: a textarea plus `btn-reject`) that posts to `/api/reject`
and displays the resulting re-prompt payload in `#reject-result`. This was
v1's implementation of the "reject that node with a comment" gesture from
`docs/02-product-concept.md` step 7, and `docs/04-roadmap.md` still lists a
real version of it under Phase 3 ("the reject button actually re-prompts
the live agent"). But the free-form prompt bar shipped since (ADR 011, ADR
037) already lets the reviewer type a targeted correction back into the
same session — the structured box is now a second, redundant affordance for
the same interim need, and it doesn't do anything the SDK-driven Phase 3
resume flow won't replace outright.

## Decision

1. Restructure `#sidebar` so only the code block (`#code-section`) scrolls
   vertically; the toggle, header/meta, why-section, and actions stay in
   view. `#sidebar` becomes a flex column that doesn't scroll itself;
   `#details` (or the code section specifically) takes `flex: 1; min-height:
   0; overflow-y: auto` so only it grows/scrolls.
2. Remove the reject-comment textarea and `btn-reject` from the UI, along
   with the now-unreachable `#reject-result` payload display and the
   `rejectNode()` wiring that only that button triggered.

## Alternatives considered

- Keep the reject box but shrink/restyle it — rejected: still a duplicate
  affordance for what the prompt bar already does, and it never worked
  end-to-end (no session-resume wiring exists yet), so keeping it mostly
  keeps confusion.
- Wire `btn-reject` into the existing continue-session prompt logic instead
  of deleting it — rejected: bigger change than asked for, and real
  node-scoped resume is explicitly Phase 3 scope; partially wiring it now
  just creates something to redo later.

## Consequences

- Sidebar becomes easier to review long code against a still-visible node
  header/status.
- The v1 "reject-as-re-prompt payload" affordance disappears from the UI;
  the reviewer's path back to the agent is the general prompt bar until
  Phase 3 builds real scoped resume.
- `/api/reject` and `ApplyEngine.reject` become dead code paths on the
  backend (no frontend caller left) but are not touched by this decision —
  see Out of scope.

## Out of scope

- Removing the backend `/api/reject` endpoint or `ApplyEngine.reject`.
  Left in place; Phase 3 (`docs/04-roadmap.md`) decides whether to
  repurpose them for real node-scoped session-resume or delete them once
  that design is settled.
- Redesigning the prompt bar to support node-scoped/targeted re-prompts
  (e.g. pre-filling it with "regarding `X`: ..."). Also Phase 3 territory.
