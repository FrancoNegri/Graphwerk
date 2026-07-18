# 105. `CheckRunner`: poll-settled check command with bounded output tail

Status: done
Decision: docs/decisions/040-post-session-check-gate.md

## Goal

A small class that runs the configured check command in a given root,
non-blocking, settled by status polls — the deterministic half of the
check gate, with the same process-ownership discipline as
`SessionRunner`.

## Acceptance criteria

- `CheckRunner(command: str, root: Path)` starts the command via
  `subprocess.Popen` with `root` as working directory; at most one child
  at a time (starting while running raises, mirroring
  `SessionBusyError`).
- `status()` is poll-driven and lock-guarded (the ticket 086 pattern):
  while the child runs it reports `running`; once the child exits it
  settles exactly once to `passed` (exit 0) or `failed` (nonzero),
  carrying the exit code and a bounded tail of combined stdout+stderr
  (last ~100 lines, hard byte cap — never the whole log).
- A command that cannot launch (`OSError`) settles immediately to a
  distinct `error` state with the exception detail, so the cycle can
  treat it as terminal rather than retrying the agent.
- Tests use stub shell commands (`true`, `false`, `echo`-loops); no real
  build tools.

## Likely files

- `graphwerk/check.py` — new module: `CheckRunner`, tail-bounding
  helper.
- `tests/test_check.py` — new.

## Out of scope

- Wiring into the session cycle (ticket 107) or CLI flags (ticket 108).
- Any parsing of the check output beyond the bounded tail.
