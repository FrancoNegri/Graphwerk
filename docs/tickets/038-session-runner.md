# 038. SessionRunner: spawn and track one headless agent session

Status: ready
Decision: docs/decisions/011-prompt-box-session-kickoff.md

## Goal

A tested Python class that can start `claude -p` in the staging worktree,
knows whether a run is active, and reports how the last one ended —
without the server or UI knowing anything about subprocesses.

## Acceptance criteria

- `SessionRunner(staged_root, claude_cmd=..., permission_mode=...)` with
  `start(prompt)`, and a `status()` snapshot: `idle` / `running` /
  `done` / `failed`, plus exit detail on failure and the last session id
  on success.
- `start()` while a run is active raises/returns a distinct "busy" outcome
  (the endpoint maps it to 409 in ticket 039).
- The child runs with the staged root as cwd and
  `--output-format json --permission-mode <mode>`; the session id is
  parsed from the JSON result when the process exits successfully.
- A missing/unlaunchable claude binary yields `failed` with a clear
  message, not an exception escaping to the caller.
- All pytest coverage uses a stub executable (tmp shell/python script)
  standing in for `claude` — the real binary is never invoked; covered:
  happy path with session id, nonzero exit, busy rejection, missing
  binary.
- No polling threads required: status may be computed lazily from
  `Popen.poll()` on each `status()` call.

## Likely files

- `graphwerk/session.py` — new class
- `tests/` — stub-binary coverage

## Out of scope

- HTTP endpoints and CLI flag (ticket 039); UI (ticket 040).
- Resume/reject flows; anything reading the transcript (existing
  rationale pipeline already covers that).
