# 044. Structured check-result summary reporting

Status: proposed
Date: 2026-07-17

## Context

ADR 040 shipped the deterministic post-session check gate (tickets 105-109):
a configured command runs after a session, and the UI shows pass/fail plus a
bounded raw output tail (last ~100 lines / 4KB, `check.py`). ADR 040 itself
flagged richer reporting as a later step ("once the plain gate proves out")
and explicitly fenced off one direction — mapping failures to graph
nodes/symbols — as out of scope for that later step too.

The gate has proven out. Two gaps remain with today's plain-tail reporting:

- **For the human reviewer:** exit code + raw text is opaque. docs/02's
  review bet ("does the stated intent match what the code does") works best
  when mechanical status is legible at a glance, not something the reviewer
  has to read a log to decode.
- **For the auto-resume loop:** `FAILURE_PROMPT_TEMPLATE` (`cycle.py`)
  already feeds the raw tail into the re-prompt as the agent's fix-relevant
  context — but the tail is bounded. A run with many failures can have its
  earlier tracebacks pushed out by later ones, so the resume prompt can
  silently omit real failures. This directly weakens Phase 3's "reject
  drives the session" bet (docs/04) before the human reject flow even
  arrives — the automatic retry already needs this.

## Decision

1. **Optional summary file.** A check command may, as its last step,
   write `.graphwerk-check.json` to the worktree root:
   ```json
   {"passed": 42, "failed": 2, "total": 44, "coverage_pct": 87.3,
    "failures": ["tests/test_foo.py::test_bar", "tests/test_baz.py::test_qux"]}
   ```
   All fields optional — operators emit whatever subset their tooling
   produces. No new CLI flag: this rides the existing `--check "<command>"`
   surface and is auto-detected by the file's presence, so it's fully
   backward compatible.

2. **`CheckRunner` (`graphwerk/check.py`) changes:**
   - `start()` deletes any pre-existing `.graphwerk-check.json` before
     launching the subprocess, so a leftover from a prior run can never be
     misread as this run's result (stale-result guard).
   - On settle, if the file exists and parses as a JSON object, its
     contents become `check_summary`; if absent or malformed, `check_summary`
     is `None` — exactly today's behavior, no new failure mode.
   - Duration is **computed by `CheckRunner` itself** (subprocess start to
     poll-settle), not sourced from the operator's file — it's free,
     accurate, and needs no operator effort.

3. **`SessionCycle` (`graphwerk/cycle.py`) changes:**
   - Status payload gains `check_summary` and `check_duration_s`.
   - `FAILURE_PROMPT_TEMPLATE`, when a summary with a non-empty `failures`
     list is present, names those failing tests explicitly and notes the
     tail below may not show all of them — directly compensating the
     tail-truncation gap. Without a summary, the resume prompt is unchanged
     from today's text.

4. **UI (`static/app.js`), thin-JS/render-only per ADR 005:**
   - Success toast becomes e.g. "✓ 42/44 tests passed in 3.2s" when a
     summary is present; unchanged "✓ check passed" when it isn't.
   - The `check_failed` banner shows parsed counts and named failures
     alongside the existing exit code + raw tail, same fallback rule.

## Alternatives considered

- **Regex heuristics over the raw tail** (parse pytest's `"12 passed, 2
  failed"`, coverage.py's `TOTAL ... 87%`, jest/go test formats, etc.) —
  zero operator effort, but a growing pile of framework-specific patterns
  that goes silently wrong or blank for anything unrecognized or
  reformatted across tool versions. Rejected.
- **Per-framework adapters** (auto-detect pytest/jest/go test, shell to
  their `--json-report`/`--json` modes) — most accurate, but couples
  graphwerk to specific test tooling, which conflicts with the check
  command being deliberately opaque (ADR 040). Rejected.
- **Tail-only resume prompt, no `failures` list** — simplest, but leaves
  the truncation gap: a many-failure run can drop earlier tracebacks from
  the bounded tail, so the auto-resume agent may never see them. Rejected
  once the resume-loop gap was identified — the `failures` list is cheap
  for operators to emit and directly closes it.

## Consequences

- No new backend dependency (stdlib `json`/`pathlib` only) and no new CLI
  surface — operators who don't emit the file see no behavior change.
- The auto-resume loop gets more complete fix-relevant context on
  many-failure runs, reinforcing docs/02's targeted re-prompting bet ahead
  of the human reject flow (Phase 3).
- `CheckRunner` grows a small parse + stale-file-guard responsibility;
  stays single-purpose (still owns exactly one check subprocess).
- No invariant touched: worktree/differ/`FileIndex` untouched; JS stays a
  render-only consumer of payload fields.

## Out of scope

- Mapping failures to specific graph nodes/symbols — still fenced by
  ADR 040's own deferral; unaffected by this decision.
- Any test-framework auto-detection or wrapping (see Alternatives).
- Historical trend across check runs — no persistence beyond the current
  cycle, per roadmap ("no DB until the graph outgrows recompute").
- Enforcing/validating the summary file's schema — malformed or partial
  JSON is silently treated as absent, never a new failure mode.
