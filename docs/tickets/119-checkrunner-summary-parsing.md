# 119. `CheckRunner` parses an optional check-result summary file

Status: done
Decision: docs/decisions/044-check-result-summary-reporting.md

## Goal

`CheckRunner` computes how long the check took and, when the check command
wrote a `.graphwerk-check.json` summary file, parses it into structured
results — while guaranteeing a stale file from a previous run can never be
misread as this run's result.

## Acceptance criteria

- `start()` deletes any pre-existing `.graphwerk-check.json` in `self.root`
  before launching the subprocess.
- After settle, `status()`'s result includes a `check_summary` key:
  - `None` if `.graphwerk-check.json` was not written by the command.
  - `None` if the file exists but is not valid JSON, or parses to something
    other than a JSON object (malformed input never raises or fails the
    check itself).
  - Otherwise, the parsed dict, passed through as-is (whatever subset of
    `passed`/`failed`/`total`/`coverage_pct`/`failures` keys are present).
- `status()`'s result includes a `duration_s` key: wall-clock seconds from
  `start()`'s subprocess launch to settle, computed by `CheckRunner` itself
  (not read from the summary file), present on every settled result
  regardless of whether a summary file was written.
- Existing `exit_code`/`tail`/`state` behavior is unchanged.

## Likely files

- `graphwerk/check.py` — stale-file removal in `start()`, summary parse +
  duration tracking in `_settle()`.
- `tests/test_check.py` — new file written / no file / malformed file /
  stale file present before `start()` / duration present cases.

## Out of scope

- Propagating `check_summary`/`duration_s` through `SessionCycle` or the
  API (ticket 120).
- Rendering the summary in the UI (ticket 121).
- Any validation of the summary schema beyond "is it a JSON object."
