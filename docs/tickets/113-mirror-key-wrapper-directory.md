# 113. Mirror key drops the src/lib wrapper directory and package root

Status: done
Decision: docs/decisions/041-paired-test-file-placement.md (amended
2026-07-17)

## Goal

Extend `_mirror_key` (`graphwerk/layout.py`, ticket 110) so a src-layout
source file mirrors its flat `tests/` counterpart, reusing
`group_for_path`'s existing wrapper-directory set instead of inventing a
second one.

## Acceptance criteria

- `src/agendabot/webhook.py` and `tests/test_webhook.py` now pair (mirror
  key `webhook.py` for both) — today they don't, since the source side
  keeps its `agendabot` package-root segment and the test side never had
  one to match against.
- The wrapper-directory-and-package-root drop applies only when the
  top-level directory is a member of `_WRAPPER_DIRECTORY_NAMES` (`src`,
  `lib`) — a plain top-level package directory (e.g. `graphwerk/layout.py`)
  keeps today's behavior (drop just the top-level directory), so
  `tests/test_layout.py` ↔ `graphwerk/layout.py` still pairs exactly as
  before.
- Nested package paths still mirror correctly once the wrapper and package
  root are dropped: `src/agendabot/bsp/twilio.py` pairs with
  `tests/bsp/test_twilio.py`.
- A wrapper-rooted path with no further segment after the package root
  (`src/only.py`, matching `group_for_path`'s own fallback case) doesn't
  crash — falls back to whatever `_mirror_key` already does for a
  same-shape path today.
- Existing ticket 110/111 tests (non-wrapper cases) are unaffected.

## Likely files

- `graphwerk/layout.py` — `_mirror_key`.
- `tests/test_layout.py` — wrapper-directory pairing coverage.

## Out of scope

- Pairing test/source files whose names don't follow the `test_`/`_test`
  convention exactly (e.g. `mock.py` vs `test_mock_adapter.py`) — the
  mirror-key convention still only proposes one candidate or none, no new
  heuristics added.
- Any change to `group_for_path` itself, which is unaffected by this
  ticket.
