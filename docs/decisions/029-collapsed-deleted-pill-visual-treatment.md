# 029. Deleted status gets a distinct hue, and keeps the faded/dashed treatment when collapsed

Status: proposed
Date: 2026-07-16

*Superseded in part by [ADR 030](030-status-palette-modified-green-deleted-red.md):*
the choice of *which* hue `deleted` gets (stone grey, chosen below
specifically to avoid clashing with `modified`'s red) no longer holds once
`modified` stops being red — ADR 030 reassigns `deleted` to red instead.
The dashed-border/reduced-opacity treatment decided here is unaffected and
still stands.

## Context

Dogfooding report: in the agendabot staging graph, `src/agendabot/webhook.py`
had ~20 helper functions/dataclasses extracted out into new files
(`business.py`, `conversation.py`, `deps.py`, `env.py`), leaving only
`health()` and the `twilio_webhook` endpoint — whose own body is untouched.
The reporter expected the collapsed `webhook.py` pill to read as changed;
instead it looked the same as an actually-untouched file (`trace/runner.py`).

Traced with the real dogfood data (`/api/graph` against
`agendabot`/`agendabot-graphwerk-staging`):

- `webhook.py`'s own file-level status, computed by the differ, is
  correctly `modified` (its bytes differ from base).
- The collapsed pill doesn't use that field. `toElements` /
  `strongestDescendantStatusByAncestor` (`static/app.js`) compute
  `collapsedStatus` purely from descendant symbol statuses, by rank
  (`modified > added > deleted > affected > unchanged`). Every remaining
  child of `webhook.py` is `deleted` (the extracted helpers), `affected`
  (`twilio_webhook`, now calling into relocated code), or `unchanged`
  (`health`) — so `collapsedStatus` correctly computes to `deleted`.
- That part is working as designed — this is a real, once-gutted file, and
  `deleted` (rank between `added` and `affected`) is a reasonable
  aggregate signal for "mostly lost its content."

The actual bug is the *rendering* of `deleted` once collapsed. An
expanded/uncollapsed node with `status: 'deleted'` gets a dashed border and
reduced opacity (`node[status='deleted']` in `static/app.js`) — a
deliberate "ghosted" look that reads as distinct from `unchanged` even
though both use muted Tailwind-slate colors (`deleted: #64748b`,
`unchanged: #475569` — one shade apart, the only two statuses that share a
hue). That selector matches the `status` attribute; collapsed containers
carry their look via `collapsedStatus` instead (`node[collapsedStatus]` /
`node[collapsedStatus][kind='file']`), so the dashed/faded cue never
applies to them. Net effect: a collapsed, mostly-deleted file renders as
flat slate — indistinguishable from a file nobody touched.

This is Phase 2 dogfood hardening (docs/04-roadmap.md, "real-repo
hardening: fix what the differ/indexer trips on") — a real-repo trip, just
in the rendering layer rather than the differ/indexer.

## Decision

Two complementary fixes, both purely in `COLORS`/styles in `static/app.js`:

1. **Give `deleted` a hue distinct from `unchanged`** instead of a shade of
   the same slate (`deleted: #64748b` → a muted warm grey, e.g. `#78716c`
   stone-500, vs. `unchanged`'s cool slate `#475569`) — so the two are
   distinguishable by color alone, not just by the dashed cue below.
2. **Extend the existing dashed-border / reduced-opacity "ghost" treatment**
   to collapsed containers whose `collapsedStatus` is `deleted`, not only
   nodes whose raw `status` is `deleted` — reinforces the distinction and
   keeps collapsed/expanded rendering consistent.

Both are client-side, view-only (collapse/expand state is inherently
client state — the same reasoning that already puts
`strongestDescendantStatusByAncestor` in `app.js` rather than the backend,
per the established view-logic-in-JS split, ADR 013/014/015), with no
backend change and no new dependency.

*Amended 2026-07-16:* originally this ADR scoped the hue change out
(narrower fix only, see rejected alternative below) — reversed after the
same dogfooding session flagged the remaining slate-on-slate similarity as
still confusing even before the dashed-treatment fix ships.

## Alternatives considered

- **Let the container's own status (`modified`) override the
  descendant-derived `collapsedStatus`** — would make this specific case
  paint red, matching the reporter's first guess. Rejected: for an
  existing file, the differ marks file-level status `modified` on *any*
  byte difference, so this would flatten today's more useful distinction —
  a file that only gained new functions currently shows a blue `added`
  pill; folding in the file's own status would repaint nearly every edited
  file red, discarding exactly the nuance `collapsedStatus` exists to
  provide.
- **Dashed treatment only, keep `deleted` as a shade of slate** — the
  original scope of this ADR; superseded per the amendment above once the
  same slate-vs-slate confusion was flagged as worth fixing on its own,
  independent of the collapsed-pill bug.

## Consequences

- Collapsed files/classes that were mostly gutted (a common shape for
  AI-driven "extract to new file" refactors) read unmistakably as "stuff
  left here," instead of blending into "untouched."
- `deleted` reads as visually distinct from `unchanged` everywhere in the
  graph (collapsed or not), not only via the dashed cue.
- Purely visual; no change to what `collapsedStatus` computes, so the
  blue/red/amber nuance for other collapse shapes is untouched.

## Out of scope

- **Symbol-move detection.** Separately confirmed during this
  investigation: a symbol whose code relocates wholesale to a new file
  currently reads as DELETE-here + ADD-there rather than a recognized
  "move," which is why `twilio_webhook` itself renders `affected` (yellow)
  rather than staying `unchanged` — it calls into symbols the differ
  treats as newly `added` elsewhere. This is a real gap (docs/03,
  hard problem #1 generalized to cross-file symbol identity) but is not
  the cause of the reported color complaint, and isn't resolved here. File
  as its own ticket if/when it becomes disruptive to review.
- Any change to how `collapsedStatus` is ranked/aggregated.
- Palette changes to `modified`/`added`/`affected` — only `deleted` was
  reported as confusable.
