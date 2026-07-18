# 107. `SessionCycle`: session → check → bounded auto-resume state machine

Status: done
Decision: docs/decisions/040-post-session-check-gate.md

## Goal

One class owns the loop: when a spawned session completes, run the check;
on failure, resume the session with the failure context, up to the retry
cap; then hand over — with every transition driven by status polls.

## Acceptance criteria

- `SessionCycle(runner, check_command | None, max_retries=1)` wraps
  `SessionRunner` (and constructs a `CheckRunner` per check run).
- With no check command configured, `status()` is a transparent
  pass-through of the runner's status — today's behavior exactly.
- Poll-driven transitions, lock-guarded: session `done` → start check
  (`checking`); check `passed` → cycle `done`; check `failed` with
  attempts left → `resume()` with the failure prompt (`resuming` →
  `running` → `checking` …); check `failed` with attempts exhausted →
  terminal `check_failed`; check `error` (unlaunchable command) →
  terminal `check_failed` with no resume; session `failed` → terminal,
  no check.
- The failure prompt is a module-level template naming the command, the
  exit code, and the output tail, and instructs the agent to fix the
  failures.
- `status()` exposes: cycle state, attempt count, and the last check's
  exit code + output tail.
- Tests drive the machine with stub runner/check states — no real
  subprocesses beyond the stub-script pattern.

## Likely files

- `graphwerk/cycle.py` — new module.
- `tests/test_cycle.py` — new.

## Out of scope

- CLI flags and `/api/session` wiring (ticket 108); UI (ticket 109).
- Retrying a check whose command itself cannot launch.
