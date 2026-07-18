# 121. Frontend renders the structured check summary

Status: done
Decision: docs/decisions/044-check-result-summary-reporting.md

## Goal

The session bar shows the structured check summary from ticket 120 when
present, so the reviewer sees test counts / coverage / duration at a
glance instead of only an exit code — falling back to today's plain
messaging whenever `check_summary` is `null`.

## Acceptance criteria

- Success toast: when `session.check_summary` is present, shows counts and
  `check_duration_s` (e.g. "✓ 42/44 tests passed in 3.2s"); when absent,
  unchanged "✓ check passed" text.
- `check_failed` banner (`renderCheckBanner`): when `session.check_summary`
  is present, shows parsed passed/failed counts and, if `failures` is
  non-empty, names them — in addition to the existing exit code + raw
  tail. When absent, banner text is unchanged from today.
- No new JS logic beyond formatting/rendering fields already present on the
  polled payload (ADR 005: render-only JS, no client-side computation of
  results).

## Likely files

- `static/app.js` — `renderSessionState`, `renderCheckBanner`, and the
  success-toast call site.

## Out of scope

- `CheckRunner`/`SessionCycle` changes (tickets 119, 120).
- Any persistence or history of past check summaries across runs.
