# 060. Skip generic wrapper directories in file grouping

Status: done
Decision: docs/decisions/021-src-layout-grouping.md

## Goal

`group_for_path` stops collapsing every file in a `src/<pkg>/...`-layout
repo into a single indistinguishable `"src"` group by skipping a small
fixed set of generic wrapper directory names and grouping by the next
path segment instead.

## Acceptance criteria

- `group_for_path("src/agendabot/bsp/models.py")` returns `"agendabot"`.
- `group_for_path("src/agendabot/webhook.py")` returns `"agendabot"`.
- `group_for_path("lib/pkg/mod.py")` returns `"pkg"` (same rule for `lib`).
- `group_for_path("tests/bsp/test_twilio.py")` still returns `"tests"`
  (not a wrapper name — unaffected).
- `group_for_path("scripts/chat.py")` still returns `"scripts"` (flat
  layout — unaffected).
- `group_for_path("src.py")` (a file literally named `src.py` at repo
  root, no directory) still returns `"."` — only a wrapper *directory*
  segment triggers the skip, not a filename.
- A repo-root file directly under a wrapper dir with nothing further
  (`src/only.py`, no package subdirectory) — group_for_path should not
  crash; falls back to `"src"` since there's no next segment to use.
- `GraphService.snapshot()` wiring test confirms `GraphNode.group` reflects
  the new grouping end to end for at least one src-layout fixture.

## Likely files

- `graphwerk/layout.py` — `group_for_path`.
- `tests/test_layout.py` — new grouping cases.

## Out of scope

- Grouping below two segments, or recognizing wrapper names beyond
  `src`/`lib` — deferred per ADR 021.
- Any change to `assign_layers`, `_layers_by_longest_path`, or the
  barycenter/grouped-ordering functions — this ticket only changes the
  group *key* computation, not layer or order.
