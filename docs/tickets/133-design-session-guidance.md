# 133. Design-session guidance module

Status: done
Decision: docs/decisions/047-design-scope-guidance-and-dialogue.md

## Goal

Spawned sessions running with `scope="design"` get a standing instruction
(same mechanism as ADR 012's `SESSION_GUIDANCE`) that pushes them toward
leaving a written, graph-legible artifact for real decisions, and toward
the exact link conventions ticket 126 already parses into `references`
edges — instead of an unstructured reply that vanishes with the process.

## Acceptance criteria

- `graphwerk/design_guidance.py` exports a `DESIGN_SESSION_GUIDANCE`
  string constant covering:
  - write a decision to `docs/decisions/NNN-slug.md` and/or a ticket to
    `docs/tickets/NNN-slug.md` (existing conventions, next-number check)
    only when a real decision/actionable step crystallized — not for
    every turn;
  - link an ADR to its tickets with inline `[NNN](../tickets/NNN-
    slug.md)` links, and keep every ticket's `Decision: docs/decisions/
    NNN-slug.md` line — the two forms ticket 126 recognizes;
  - ground itself in `docs/02-product-concept.md`, `docs/04-roadmap.md`,
    and `CLAUDE.md` before proposing a decision, same material
    `north-star` re-reads.
- `SessionRunner.start()` and `SessionRunner.resume()`
  (`graphwerk/session.py`) append `DESIGN_SESSION_GUIDANCE` to the
  `--append-system-prompt` text only when called with `scope="design"`;
  `scope="implementation"` and `scope=None` build the exact same command
  as today (regression-tested).
- A round-trip-style test (same spirit as `tests/rationale/
  test_guidance.py`) asserts the guidance text contains the literal link
  formats ticket 126's extractor matches, so guidance wording and parser
  behavior can't silently drift apart.

## Likely files

- `graphwerk/design_guidance.py` — new, the constant.
- `graphwerk/session.py` — `start()`/`resume()` gain the scope-conditional
  append.
- `tests/test_design_guidance.py` — new.
- `tests/test_session.py` — scope="design" vs. other scopes build
  different commands.

## Out of scope

- Anything about the reply/dialogue surface — ticket 134/135.
- Literal `north-star` skill-file invocation (ADR 047, Alternatives).
