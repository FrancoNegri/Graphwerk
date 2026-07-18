# 045. Persistent, prominent "Checks" status; standing name for the concept

Status: proposed
Date: 2026-07-18

## Context

ADR 040/044 shipped the deterministic post-session check gate and its
structured summary (tickets 105-121, all done). In practice, dogfooding it
surfaced a gap: once a session finishes, the only success signal is a toast
that self-dismisses after 3s (`toast()`, `static/app.js`), and the only
failure signal is a dismissible banner. There is no persistent, at-a-glance
indicator of whether the last checks passed, failed, are running, or were
never configured at all — a user who glances at the screen after the toast
has faded sees a session marked "done" with **no visible result**, exactly
docs/02's "review starts from a known-good (or known-bad, loudly) worktree"
bet failing in practice.

A second, related gap: `SessionCycle.status()` returns the bare
`SessionRunner.status()` when no `--check` command is configured at all
(`cycle.py:63-64`), so there is no field distinguishing "checks not
configured for this run" from any other state. The frontend currently
infers "a check cycle happened" via `"attempt" in session`
(`app.js:796`), an implicit, easy-to-miss signal rather than an explicit one.

Separately, the user asked for a better standing name for the concept than
"check gate" — something generic enough to cover tests, builds, and lint
alike, since a check command can be any of those.

Both fit squarely inside Phase 3 (docs/04): this is a UX/legibility
follow-up to already-shipped, in-scope work, not a new feature or a detour.

## Decision

1. **Naming: adopt "Checks" going forward**, not a code/API rename. Use
   "Checks" (capitalized, plural, no "gate" suffix) as the standing
   user-facing term in new UI copy and new docs — it already matches the
   existing `check_*`/`--check` vocabulary in the code, needs no renaming
   of CLI flags, class names, or JSON payload fields, and reads as generic
   (tests/build/lint) rather than test-specific. The user's suggested
   "post-change checks and builds" is accurate but too long for a UI label;
   "Checks" carries the same meaning. Existing ADRs/tickets (040, 044,
   105-121) are historical record and are not rewritten.

2. **`SessionCycle.status()` always reports whether checks are configured.**
   Add a `check_configured: bool` field to every payload, including the
   no-`--check` path that currently bypasses the wrapper — that path keeps
   returning the runner's own state/fields unchanged, just with
   `check_configured=False` added. This replaces the frontend's implicit
   `"attempt" in session` inference with an explicit field.

3. **A persistent "Checks" status indicator in the session bar**, always
   visible (not toast-dependent), reflecting one of: **not configured**
   (`check_configured` is `False`), **running** (state is `checking` or
   `resuming` — reuses the existing busy label), **passed**, or **failed**.
   It updates in place on every poll and does not self-dismiss — the
   *next* session start is what resets it to "running." The existing
   `check_failed` banner (full output tail, named failures) stays as the
   dismissible drill-down for failure detail; the indicator is the
   always-on summary that the banner and toast were never meant to be.

4. **Fix the one hardcoded test-specific string.** The success toast's
   `formatCheckPassedToast` (`app.js:801-810`) always says "N/M **tests**
   passed" — wrong when the check command is a build or lint step. Rephrase
   to be neutral of what kind of check ran (e.g. drop "tests", or say
   "checks" generically), matching the "generic enough to cover
   tests/build/lint" goal from (1).

## Alternatives considered

- **Extend the toast's duration / add a history log panel of past runs** —
  doesn't fix the "not configured" blind spot, and a history panel
  conflicts with ADR 044's explicit deferral of check-result persistence
  across runs ("no DB until the graph outgrows recompute", docs/04).
  Rejected.
- **Reuse the failure-banner component for success too** — noisier for the
  common case (every passing run pops a dismissible banner) and semantically
  odd ("banner" implies something needs attention). A quiet, persistent
  status chip fits the common case better; the banner stays reserved for
  failure detail. Rejected.
- **Rename the code-level vocabulary** (`--check` → `--verify`, `CheckRunner`
  → something else, `check_summary` → renamed field) — touches CLI flags,
  the API payload contract, and every test across tickets 105-121 for a
  cosmetic-only gain, and `--verify`-shaped names collide with the existing
  `/verify` skill's different meaning (driving the app to observe behavior
  manually). Rejected in favor of a docs/UI-copy-only naming decision.

## Consequences

- Closes the "finished but no visible result" gap docs/02's review bet
  depends on, without adding any new persistence surface.
- `check_configured` is additive and backward compatible — existing
  consumers of `/api/session` gain a field, nothing is renamed or removed.
- No invariant touched: JS stays a render-only consumer of payload fields
  (ADR 005); no new backend dependency; CLI surface and API field names are
  unchanged.
- Small ongoing cost: future docs/UI copy should say "Checks," not
  "check gate," but no enforcement mechanism beyond convention.

## Out of scope

- Renaming CLI flags, class names, or existing API field names (see
  Alternatives) — revisit only if the current vocabulary causes real
  confusion in practice, not for cosmetic consistency alone.
- Historical/trend view across past check runs — still fenced by ADR 044.
- Mapping check failures to graph nodes/symbols — still fenced by ADR 040.
- Any change to retry/resume/auto-fix logic itself.
