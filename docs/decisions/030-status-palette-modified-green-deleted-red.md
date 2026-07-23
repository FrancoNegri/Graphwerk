# 030. Status palette: `modified` turns green, `deleted` turns red

Status: proposed
Date: 2026-07-16
Supersedes: 029

*[ADR 031](031-modified-status-blue-not-green.md) briefly proposed cyan for
`modified` instead; rejected same day after seeing it rendered, before any
ticket shipped. `modified` stays green, as decided here.*

## Context

Explicit user request: recolor the status palette so `modified` reads green
and `deleted` reads red. Today: `modified: #ef4444` (red), `added: #3b82f6`
(blue), `deleted: #64748b` (slate), `affected: #f59e0b` (amber),
`unchanged: #475569` (slate). This is the same palette
[02-product-concept.md](../02-product-concept.md) states as part of the
concept itself ("modified symbols in red, new ones in blue, deleted in
grey") and [03-architecture-notes.md](../03-architecture-notes.md) repeats
("red = modified, blue = new, grey = deleted, yellow = affected caller") —
so this isn't a pure implementation detail, it's touching something the
concept doc treats as settled.

It also directly reopens [ADR 029](029-collapsed-deleted-pill-visual-treatment.md),
closed earlier *today*, which picked a slate/stone grey for `deleted`
specifically *to avoid colliding with `modified`'s red* ("the only two
statuses that share a hue" was the bug being fixed — grey vs. grey, not
grey vs. red). Once `modified` stops being red, that constraint disappears,
so reopening is legitimate rather than flip-flopping — but it should be
recorded as a supersession, not a silent overwrite.

This is a stylistic preference, not a dogfooding-hardening fix — a detour
from Phase 2's stated exit criterion (build-a-graphwerk-feature-using-
graphwerk). Flagging that plainly per this skill's step 2; proceeding
because the user asked for it directly, twice, after the tradeoffs were
raised.

**Real coupling found while checking this:** `static/style.css` reuses the
status palette's CSS variables for unrelated UI chrome, not just node/edge
status:
- `#prompt-error { color: var(--modified); }` — the inline prompt-error
  text borrows `--modified` purely because it happened to be red, i.e. it
  means "danger," not "modified status." Repainting `--modified` green
  would silently turn error text green. This is a real bug this change
  would introduce if not handled, not a hypothetical.
- `--added` is similarly reused as the general accent color (buttons,
  spinner, checkbox accent, the `.why` callout border) — unaffected here
  since `added` isn't changing, but worth naming so a future palette change
  doesn't repeat this mistake blind.

## Decision

1. `COLORS.modified` (`static/app.js`) and `--modified` (`static/style.css`):
   `#ef4444` → `#22c55e` (green-500). Chosen a shade more saturated than
   the code-diff panel's existing added-line green (`#4ade80`, green-400)
   so the two read as related-but-distinct rather than identical — a
   modified-status node and an added *line* inside its diff both being
   "green family" is coherent (git-diff convention: green means
   new/changed-for-the-better content), not a collision.
2. `COLORS.deleted` (`static/app.js`) and `--deleted` (`static/style.css`):
   → `#ef4444` (the red `modified` just vacated — no new hex needed).
   This actually *improves* alignment with the code-diff panel's existing
   removed-line red (`#f87171`, red-400): deleted-status red (red-500) and
   removed-line red (red-400) now relate the same way modified/added-line
   green do.
3. Decouple `#prompt-error` from the status palette: add a `--danger:
   #ef4444` custom property in `:root` and point `#prompt-error` at it
   instead of `var(--modified)`. Keeps error text red regardless of what
   `--modified` is, and stops "error" and "modified-status" from being the
   same variable by coincidence.
4. `added` (`#3b82f6`), `affected` (`#f59e0b`), and `unchanged` (`#475569`)
   are untouched — not reported as confusing, out of scope per ADR 029 and
   still true here.
5. [ADR 029](029-collapsed-deleted-pill-visual-treatment.md)'s
   dashed-border/reduced-opacity treatment for `deleted` (collapsed or
   expanded) stands unchanged — this ADR only supersedes *which hue*
   `deleted` uses, not whether it gets the ghosted treatment. [Ticket
   078](../tickets/078-collapsed-deleted-pill-dashed-treatment.md) is
   amended in place to reference the new hex rather than superseded
   wholesale, since the dashed-treatment acceptance criteria it describes
   are still exactly what's wanted.
6. The illustrative color mentions in
   [02-product-concept.md](../02-product-concept.md) and
   [03-architecture-notes.md](../03-architecture-notes.md) are updated to
   match (concept-doc text, not app code — edited directly as part of this
   ADR rather than deferred to a ticket).

## Alternatives considered

- **Do nothing (keep today's palette)** — respects ADR 029's ink barely
  dry and the concept doc's example as-is. Rejected: the user asked
  directly, twice, understanding the tradeoffs raised.
- **Full git-status-convention reshuffle** (`added` → green to match
  git's added-line convention, `modified` → a third color such as amber/
  blue since git tooling rarely colors "modified" green or red, `deleted`
  → red) — arguably more convention-aligned, but reshuffles three colors
  instead of two and touches `added`, which nothing reported as confusing.
  Rejected as broader than what was asked; can revisit later if `added`
  vs. `modified` (both would then be in the blue/green family) turns out
  to read ambiguously in practice.
- **Reuse the diff panel's exact line-level hex values** (`#4ade80` for
  modified, `#f87171` for deleted) instead of picking distinct 500-weight
  shades — rejected: would make the status-level color and the line-level
  diff color literally identical, losing the "these are related but
  operating at different granularity" visual cue the 500-vs-400 shade gap
  gives.

## Consequences

- `modified` and `deleted` read as green/red — the most git-diff-familiar
  pairing, at the cost of departing from this project's own founding
  color example (updated in docs/02-03 to match, so the docs stay
  accurate rather than stale).
- The `#prompt-error` coupling is fixed as part of this change, not left
  as a latent bug — error text stays legibly red no matter what the status
  palette does next.
- Call edges (`edge[kind='calls']`), which already color by
  `COLORS[status]`, pick up the new green/red automatically — no separate
  edge-coloring work needed.
- Any *future* palette change should grep for `var(--modified)` /
  `var(--added)` / `var(--deleted)` usage first — this ADR is the second
  time in one day a "just recolor X" request turned up a non-obvious
  coupling; worth remembering as a standing check, not just fixing here.

## Out of scope

- Reshuffling `added`/`affected`/`unchanged` — not reported as confusing.
- Any change to `collapsedStatus` ranking/aggregation (ADR 029's
  out-of-scope, still holds).
- Symbol-move detection (ADR 029's out-of-scope, still holds; unrelated to
  color).
