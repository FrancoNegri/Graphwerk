# 013. Import edges resolve src-layout and package roots

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md

## Goal

Import edges appear on real repos that keep code under a package root
(`src/pkg/...`): running against agendabot, only 12 of the graph's import
edges exist — all between test files — because `_add_import_edges` maps
`src/agendabot/store.py` to module key `src.agendabot.store`, which never
matches the `agendabot.store` that import statements actually name. This
also blunts ticket 012's layer banding (found while verifying ticket 011:
nearly every agendabot file lands in layer 0).

## Acceptance criteria

- A file at `src/pkg/mod.py` gets an import edge from a file containing
  `import pkg.mod` (or `from pkg.mod import x`): module names resolve
  against dotted-path *suffixes* of known files, not only full paths.
- `from pkg import x` resolves to `pkg/__init__.py` (and the src-layout
  equivalent `src/pkg/__init__.py`).
- Ambiguous suffixes emit no edge: with both `a/utils.py` and
  `b/utils.py` present, `import utils` matches neither (no guessing).
- An exact full-dotted-path match still wins over suffix matching, so the
  flat-layout demo graph is unchanged (same edges as before).
- Covered by pytest tests alongside the existing suite.

## Likely files

- `graphwerk/service.py` — `_add_import_edges` module→file resolution
  (extract a small resolver if it stops being a dict lookup).
- `tests/` — resolver tests.

## Out of scope

Relative imports (`from . import x` — the indexer currently drops the
level); namespace packages; resolving imports to third-party modules.
