# 031. `modified` status turns blue, not green

Status: rejected
Date: 2026-07-16

*Rejected same day, before implementation shipped:* after seeing cyan
rendered in the actual running UI (dogfood graph, `webhook.py` subtree),
the user rolled the request back and kept `modified` green per [ADR
030](030-status-palette-modified-green-deleted-red.md). Recorded rather
than deleted, per this project's never-delete-just-supersede convention
(cf. ADR 018) — the reasoning below (why cyan over indigo/sky, the
distinguishability constraint against `added`'s blue) stays available if
blue-for-`modified` comes up again.

## Context

Explicit user request, made while tickets 079/080 (implementing ADR 030)
were still in progress this session, before either was marked `done`:
`modified` should be blue instead of green.

This directly reopens ground ADR 030 itself already covered. ADR 030's
"Alternatives considered" section explicitly weighed and rejected a
broader reshuffle that would have put `modified` in the same hue family as
`added` (`#3b82f6`, blue-500) — "arguably more convention-aligned, but
reshuffles three colors instead of two... Rejected as broader than what
was asked; can revisit later if `added` vs `modified` ... turns out to
read ambiguously in practice." That's exactly the revisit happening now,
at the user's explicit direction rather than because anything broke.

Constraint this reopens: `added` is staying blue-500 (`#3b82f6`, untouched
by any ticket so far). `modified` turning blue too needs a shade
distinguishable from `added` at a glance — two status colors that both
read as "blue" defeats the purpose of a status palette. This is Phase 2
dogfood-adjacent styling, same as ADR 030 — a detour from Phase 2's actual
exit criterion, flagged here for the same reason, proceeding because the
user asked directly.

## Decision

`COLORS.modified` (`static/app.js`) and `--modified` (`static/style.css`):
`#22c55e` → `#06b6d4` (cyan-500).

Cyan-500 sits well clear of `added`'s blue-500 (`#3b82f6`) — a
blue-vs-cyan contrast reads as two distinct colors at pill/edge scale,
where a closer pick (e.g. indigo, sky) risks blending with `added` at a
glance, exactly the ambiguity ADR 030 flagged as the reason not to do this
reshuffle casually. Cyan also stays clear of the violet/indigo directory
tints (`DIR_TINTS` in `static/app.js`, e.g. `#4c1d95`) used for background
grouping, so there's no new near-collision with an unrelated part of the
palette.

`deleted` (`#ef4444`, red) is unaffected — nothing about this request
touches it, and it still benefits from the same separation-from-`modified`
reasoning ADR 030 already established, just against blue instead of green
now.

No existing ticket needs to be created for this: [ticket
079](../tickets/079-modified-status-turns-green.md) already scopes exactly
"recolor `COLORS.modified` + `--modified`, verify legend/chip/edge" and
hadn't shipped yet — amended in place to the new hex, same as ADR 030 did
to ticket 078 for the same reason (forking a duplicate ticket over a
value-only change before the original ships would just be churn).

## Alternatives considered

- **Indigo-500 (`#6366f1`)** — stays closer to conventional "blue," but
  only ~20° of hue separation from `added`'s blue-500; more likely to read
  as "the same blue" at small pill/edge sizes, and nudges toward the
  violet directory-tint range. Rejected for weaker distinguishability,
  which is the whole reason this needs a considered pick rather than
  defaulting to the nearest blue.
- **Sky-500 (`#0ea5e9`)** — a middle option between `added`'s blue and
  cyan; better separation than indigo but less than cyan-500. Rejected in
  favor of the larger, safer margin cyan-500 gives, since the two colors
  sit adjacent in the UI (node fill/border, legend dot, edge color) where
  small differences matter more than they would in isolation.
- **Keep green (do nothing)** — respects ADR 030 as freshly decided.
  Rejected: the user asked directly, this session, before 030's tickets
  even closed out.

## Consequences

- `modified` and `added` are both cool colors now (cyan vs. blue) rather
  than `modified` sitting in the warm green ADR 030 chose — loses the
  coherence ADR 030 drew between status-level green and the diff panel's
  added-line green (`#4ade80`); there's no equivalent existing blue/cyan
  line-level color in the diff panel to relate to, so that link is simply
  gone, not replaced.
- `deleted` (red) and `modified` (cyan) are still maximally distinct in
  temperature (warm/cool), preserving the git-diff-familiar "red bad,
  not-red not-bad" read even though the specific "not-red" hue changed.
- Ticket 079 is amended in place rather than superseded wholesale, per the
  established pattern from ADR 030 → ticket 078.

## Out of scope

- `deleted` staying red, `added`/`affected`/`unchanged` staying as ADR 030
  left them — none of this is touched.
- The `--danger`/`#prompt-error` decoupling (ticket 080) — unaffected,
  already independent of `--modified`'s specific value by design.
- Any further palette reshuffling — if `added` vs. `modified` still reads
  ambiguously after this ships, that's a new decision, not assumed here.
