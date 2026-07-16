# 021. Skip generic wrapper directories when grouping files by top-level directory

Status: accepted
Date: 2026-07-16

## Context

ADR 010 grouped files within a layer band by top-level directory
(`group_for_path`: first path segment) and explicitly deferred going
deeper, conditioned on *"revisit if top-level proves too coarse on real
repos."* The agendabot dogfood run is that evidence: `group_for_path`
takes `src/agendabot/...` → `"src"` for every file in the package, so 50
of 103 file nodes in the current graph — the entire `agendabot` source
tree, spanning `bsp/`, `calendar/`, `db/`, `models/`, `parsers/`,
`trace/`, `validators/`, and the top-level modules — share one
indistinguishable group. `env.py` (a brand-new config module) and
`bsp/models.py` (an existing, unrelated domain-models file) tint
identically and can share a layer band with no group cue to tell them
apart, because the reviewer-facing signal ADR 010 introduced ("these
chips are `tests`, those are `src`") only discriminates the outermost
`src`/`tests` split and goes silent for everything inside `src`.

This directly undercuts the product concept's "structural context"
promise (docs/02) that ADR 002/010 exist to serve, and it's discovered
via real-repo dogfooding per Phase 2's "Real-repo hardening" line
(docs/04) — the same kind of finding tickets 008/009/013/054 came out of.
It is not a redesign of `layer` (import depth): that axis was checked
against the same dogfood data during this pass and is doing exactly what
ADR 002 specifies. Only the directory-grouping axis is short.

## Decision

Teach `group_for_path` (`graphwerk/layout.py`) to skip a small fixed set
of generic wrapper directory names — `{"src", "lib"}` — when they are the
first path segment, and group by the next segment instead:

- `src/agendabot/bsp/models.py` → group `"agendabot"` (was `"src"`)
- `src/agendabot/webhook.py` → group `"agendabot"` (was `"src"`)
- `tests/bsp/test_twilio.py` → group `"tests"` (unchanged — `tests` isn't
  a wrapper name, so it still groups at one level, matching ADR 010's own
  worked example)
- `scripts/chat.py` → group `"scripts"` (unchanged — flat layout, no
  wrapper prefix)

Grouping still stops after one further segment (no recursive descent into
`bsp/` vs `calendar/` vs `db/`) — the smallest change that fixes the
observed collapse, not a general N-level grouping scheme.

Stays entirely inside `graphwerk/layout.py`, stdlib-only, covered by
`tests/test_layout.py`. `GraphNode.group` and the UI tint/legend (ADR
010) are unchanged as a contract — they just receive better-discriminated
values.

## Alternatives considered

- **Reuse the src-layout root detection from ticket 013** — rejected on
  inspection: ticket 013's import-edge resolver matches module dotted-path
  *suffixes* against file paths; it never materializes an explicit
  "package root" fact that grouping could read. Building one would be new
  machinery for a problem a two-line fixed-set check already solves.
- **Always group by the first two path segments** — simpler rule, no
  wrapper-name list, but it also splits `tests/` into `tests/bsp`,
  `tests/trace`, etc., undoing the one grouping axis (`tests` as a single
  legible run) that ADR 010's dogfood evidence showed working. Rejected —
  fixes an unreported problem while breaking a working one.
- **Configurable grouping depth** — most flexible, but adds a config
  surface the project doesn't otherwise have (CLAUDE.md keeps backend deps
  and knobs minimal), and doesn't fix the default experience, which is
  what the dogfood run actually surfaced. Rejected, same spirit as ADR
  010's own rejection of two-dimensional lanes for a first increment.

## Consequences

- `agendabot`'s ~50 `src` files split into one real group instead of one
  fake one; the tint/legend ADR 010 shipped starts actually discriminating
  inside the package, at no UI cost (it already renders whatever string
  `group` carries).
- Flat-layout repos (no `src`/`lib` wrapper) and the `tests`/`scripts`
  split are byte-for-byte unaffected — verified against the existing
  `test_layout.py` grouping cases plus a new src-layout case.
- Touches no invariant: stdlib-only, server-side (ADR 005), no new
  extractor, no JS logic change.

## Out of scope

- Grouping below two segments (`bsp` vs `calendar` vs `db` as their own
  visual groups) — no evidence yet this repo needs it; revisit only if a
  dogfood run shows the two-level group still too coarse.
- Recognizing wrapper names beyond `src`/`lib` (e.g. monorepo
  `packages/*/src/`) — no case observed yet; extend the fixed set later if
  one shows up.
- Compound directory parent nodes / 2D directory×layer lanes — still
  deferred per ADR 010's own out-of-scope, unchanged by this decision.
- Any change to `layer` (import-depth) semantics — checked against the
  same dogfood data this pass; it's working as ADR 002 specifies and isn't
  part of this problem.
