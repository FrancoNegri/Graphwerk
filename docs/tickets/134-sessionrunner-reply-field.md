# 134. SessionRunner exposes the session's reply text

Status: ready
Decision: docs/decisions/047-design-scope-guidance-and-dialogue.md

## Goal

`SessionRunner._settle()` currently parses the CLI's `--output-format
json` output only far enough to extract `session_id`, discarding the
assistant's actual reply text. Expose it as a `reply` field on the status
dict so a design-mode dialogue surface (ticket 135) has something to
render, without changing what happens when there's nothing to show.

## Acceptance criteria

- `SessionRunner._settle()` extracts the final `type == "result"` event's
  reply text (the same event `_session_id_from` already locates) and
  stores it; `status()`/`_status_locked()` includes it as `reply` (empty
  string, not `None`, when a run produced no result event or failed —
  matches `detail`'s existing empty-string-on-nothing convention).
- `SessionCycle.status()`/`start()`/`continue_session()` require **no
  code change** — confirm with a test that `reply` passes through both
  the `check_command is None` path and the checked path, since both
  already copy the runner's status dict wholesale before overwriting only
  the fields `SessionCycle` owns.
- `/api/session` and `/api/prompt` responses carry `reply` with no
  `graphwerk/server.py` change (both endpoints return the dict as-is).
- Existing tests asserting the shape of `SessionRunner`/`SessionCycle`
  status payloads still pass; a new test pins that `reply` reflects the
  latest turn only (a second `start()`/`resume()` replaces it, no
  accumulation server-side — accumulation is the frontend's job in ticket
  135).

## Likely files

- `graphwerk/session.py` — `_settle()`, `_status_locked()`.
- `tests/test_session.py` — reply extraction, empty-string-on-failure.
- `tests/test_cycle.py` — passthrough assertion (no `cycle.py` edit
  expected; a failing test here would mean the "no code change" premise
  was wrong).

## Out of scope

- Any frontend rendering (ticket 135).
- Multi-turn history / accumulation of replies — server stores only the
  latest, same as it already does for `session_id`/`detail`.
