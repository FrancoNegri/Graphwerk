# 138. `build_app()` factory

Status: done
Decision: docs/decisions/049-build-app-factory-extracted-from-cli.md

## Goal

Move the FastAPI-app wiring currently inline in `cli.py::_serve()` into a
standalone `build_app()` function in a new `graphwerk/bootstrap.py` module,
so constructing a fully-wired app is a single reusable call instead of a
composition block copy-pasted at every call site.

## Acceptance criteria

- `graphwerk/bootstrap.py` exports `build_app(base, staged, sidecar,
  transcript, agent_permissions, check_command=None, check_retries=1) ->
  FastAPI`, containing exactly the construction logic currently in
  `cli.py::_serve()` (RationaleStore, GraphService, ApplyEngine,
  SessionRunner, SessionCycle, CommitEngine, DiscardEngine, `create_app`)
  with no behavior change.
- `cli.py::_serve()` calls `build_app()` and no longer imports the engine
  classes it previously constructed directly (it still imports whatever it
  needs for argparse/uvicorn/printing).
- `server.py` is unchanged.
- Existing CLI tests (`tests/test_cli.py`) and server tests
  (`tests/test_server.py`) continue to pass unmodified — this ticket does
  not touch test files.
- A new test for `build_app()` asserts it returns a `FastAPI` instance
  wired to real base/staged temp directories (mirrors the setup already
  used in `tests/test_cli.py` or `tests/test_server.py`).

## Likely files

- `graphwerk/bootstrap.py` — new file, `build_app()`.
- `graphwerk/cli.py` — `_serve()` shrinks to call `build_app()` + `uvicorn.run()`; drop now-unused engine imports.
- `tests/test_bootstrap.py` — new file, one test covering `build_app()`.

## Out of scope

- Updating `tests/test_server.py` fixtures to use `build_app()` instead of
  their own hand-wired construction (separate cleanup, not required for
  this ticket's acceptance criteria).
- Any change to route definitions in `server.py` or to the engine classes.
