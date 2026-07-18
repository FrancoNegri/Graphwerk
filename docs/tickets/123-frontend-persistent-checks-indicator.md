# 123. Persistent "Checks" status indicator in the session bar

Status: done
Decision: docs/decisions/045-persistent-checks-status-and-naming.md

## Goal

The session bar shows an always-visible "Checks" status — not configured /
running / passed / failed — driven by `check_configured` (ticket 122) and
the existing `state`/`check_summary`/`check_exit_code` fields, so a passed
or failed result stays visible after the toast fades and after a "not
configured" run is distinguishable from silence.

## Acceptance criteria

- A new persistent element (e.g. `#checks-indicator`) in the session bar,
  always rendered (never hidden), showing one of:
  - `check_configured === false` → "Checks: not configured"
  - `state` is `checking` or `resuming` → "Checks: running…" (or the
    existing busy label)
  - `state === "done"` and checks ran → "Checks: passed" plus counts/
    duration when `check_summary` is present (reusing the same
    passed/total/duration formatting the toast used)
  - `state === "check_failed"` → "Checks: failed" plus counts when present
  - It updates in place on every poll; it is not dismissible and does not
    self-clear — only the next session start changes it.
- The existing `check_failed` banner (raw tail, named failures list) is
  unchanged — it remains the dismissible drill-down; the indicator is
  additive, not a replacement for it.
- The success toast's `formatCheckPassedToast` no longer hardcodes "tests
  passed" — rephrase generically (e.g. drop "tests", since a check command
  can be a build or lint step too).
- Render-only: no new client-side computation of pass/fail, only formatting
  of fields already present on the polled payload (ADR 005).

## Likely files

- `static/app.js` — `renderSessionState`, new `renderChecksIndicator`,
  `formatCheckPassedToast` wording fix.
- `static/index.html` (or wherever the session bar markup lives) — new
  indicator element.
- Any CSS backing the session bar, for a passed/failed/not-configured
  visual treatment (color, consistent with existing status palette).

## Out of scope

- `SessionCycle`/`CheckRunner` backend changes (ticket 122, already covers
  the field this consumes).
- Any renaming of CLI flags, class names, or API field names (ADR 045,
  Alternatives).
- Historical/past-run display.
