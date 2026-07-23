# 193. Backfill `Supersedes:`/`Amends:`/`Extends:` lines into existing ADRs

Status: ready
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

Existing ADRs whose own prose already unambiguously states a supersede/
amend/extend relationship get the new machine-readable line added — so
the graph shows real lineage from day one, not just for ADRs written after
this ticket.

## Acceptance criteria

- Every ADR whose text already says, in so many words, that it supersedes,
  amends, or extends another specific ADR gets the corresponding new line
  added under its `Status:`/`Date:` header. Starting set already found in
  this repo's own docs (verify each still reads accurately before adding
  the line, don't add mechanically without checking the specific ADR
  numbers named):
  - 058 → `Supersedes: 037, 050`
  - 061 → `Amends: 058`
  - 042 → `Supersedes: 037`
  - 015 → `Supersedes: 002`
  - 041 → `Extends: 005`
  - 050 → check against 058's supersession — 058 already claims to
    supersede 050; confirm no line is needed on 050 itself (the relation
    is recorded on the superseding ADR, not the superseded one).
  - Any other case found by grepping `docs/decisions/*.md` for
    "supersed*"/"amend*"/"extend*" during this ticket's own work — the
    list above is a starting point, not exhaustive.
- A test asserts every `Supersedes:`/`Amends:`/`Extends:` line across
  `docs/decisions/*.md` resolves to a real, existing ADR file (guards
  against a future typo as much as this backfill).
- No prose is rewritten — this only adds the new front-matter line where
  a relationship is already stated in words.

## Likely files

- `docs/decisions/058-*.md`, `061-*.md`, `042-*.md`, `015-*.md`,
  `041-*.md`, and any others found during the ticket's own grep pass.
- `tests/` — the resolves-to-a-real-file check (likely alongside ticket
  191's parser tests).

## Out of scope

- Adding relationship lines for relationships that are only loosely
  implied, not stated outright — when in doubt, leave it out; a missing
  edge is far less costly than a wrong one on a review surface.
- Any change to an ADR's actual decision/consequences text.
