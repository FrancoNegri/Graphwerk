# 049. `build_app()` factory extracted from `cli.py`

Status: accepted
Date: 2026-07-18

## Context

Raised as: "the cli and the server are using and importing a lot of the same
classes — should we separate the concerns properly?"

Inspection of `graphwerk/cli.py` and `graphwerk/server.py` shows the split is
already correct: `server.py::create_app()` never constructs `GraphService`,
`ApplyEngine`, `CommitEngine`, `DiscardEngine`, `SessionCycle`, or
`SessionRunner` — it only receives them as parameters and imports their names
for type hints. All construction happens in one place, `cli.py::_serve()`,
which acts as the composition root for all three subcommands (`demo`,
`serve`, `start`). This is dependency injection working as intended, not
entanglement, and doesn't call for an architectural change.

The one real smell: `_serve()`/`_start()` in `cli.py` do three unrelated
jobs in one function — parse-derived wiring of five engine objects, and
launching uvicorn — with no reusable seam between "build the FastAPI app"
and "run it as a process." `tests/test_server.py` pays for this today: it
hand-repeats the same five-line construction block (`GraphService`,
`ApplyEngine`, `CommitEngine`, `DiscardEngine`, `SessionCycle`) five separate
times because there's no factory to call instead.

This isn't tied to a specific roadmap-phase goal — it's a small internal
code-organization cleanup, not a feature. It doesn't touch any product
concept or Phase 2 exit criterion, so it's being scoped minimally rather
than treated as a detour worth deferring.

## Decision

Extract the wiring block out of `cli.py::_serve()` into a new function
`build_app()` in a new module `graphwerk/bootstrap.py`:

```python
def build_app(base: Path, staged: Path, sidecar: Path | None,
               transcript: Path | None, agent_permissions: str,
               check_command: str | None = None,
               check_retries: int = 1) -> FastAPI:
    ...  # exact body of today's _serve(), minus the uvicorn.run() call
```

`cli.py::_serve()` shrinks to: call `build_app()`, print the URL, call
`uvicorn.run()`. No behavior changes — this moves code, it doesn't alter it.
`server.py` is untouched; it keeps owning only route definitions.

## Alternatives considered

- **Leave it in `cli.py`** — costs nothing today, but keeps `_serve` doing
  three jobs and keeps tests hand-rolling the same construction block.
- **Wrap construction in a class (`GraphwerkApp.create(...)`)** — no benefit
  over a plain function here; there's no state to hold between construction
  and use, so a class adds a layer without buying anything.

## Consequences

Makes it easier to: reuse the exact same wiring in tests (`build_app()`
instead of five lines of construction), and add a future non-CLI entry point
without duplicating wiring. Makes harder: nothing — it's a pure move. No
architecture invariant is touched (no new dependency, no change to the
worktree/diff/apply model, no JS outside `static/`).

## Out of scope

- Migrating `tests/test_server.py`'s existing hand-wired fixtures to call
  `build_app()` — worth doing later as cleanup, not bundled into this
  ticket since it touches many call sites for no behavior change.
- Any change to `server.py`'s route layer or to the engine classes
  themselves.
