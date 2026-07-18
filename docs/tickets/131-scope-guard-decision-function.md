# 131. Scope-guard decision function

Status: ready
Decision: docs/decisions/046-knowledge-base-graph-and-design-dialogue.md

## Goal

A pure, fully unit-testable function decides whether a tool call's target
path is allowed under a given session scope — the deterministic logic
behind the hard design/implementation write boundary, kept separate from
the Claude Code hook plumbing that invokes it (ticket 132).

## Acceptance criteria

- `graphwerk/hooks/scope_guard.py`: `is_allowed(scope: str | None, path:
  str) -> bool`.
  - `scope is None` (unscoped) → always `True` — today's unrestricted
    behavior, no regression for callers that don't opt in.
  - `scope == "design"` → `True` only for paths ending in `.md`.
  - `scope == "implementation"` → `True` for every path *not* ending in
    `.md`.
- A small CLI-invokable wrapper (`main()` or `__main__` entry) that reads
  a Claude Code PreToolUse hook's tool-call payload (per Claude Code's
  hook protocol — consult current hook docs for the exact JSON shape) and
  emits the matching allow/deny decision. Kept thin: all the actual logic
  is in `is_allowed`.

## Likely files

- `graphwerk/hooks/scope_guard.py` — new module.
- `tests/test_scope_guard.py` — `is_allowed` cases for all three scope
  values, `.md` and non-`.md` paths, nested paths.

## Out of scope

- Wiring this into `SessionRunner`/spawning the hook config (ticket 132).
- Any non-extension-based scoping (e.g. a configurable docs-path glob) —
  `.md`-vs-not is the whole rule for v1.
