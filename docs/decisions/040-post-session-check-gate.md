# 040. Deterministic post-session check gate with bounded auto-resume

Status: proposed
Date: 2026-07-17

## Context

Today a spawned session (ADR 011) ends and control returns to the user
immediately — whatever state the worktree is in. Nothing deterministic
stands between "the agent says it's done" and "the human starts
reviewing." Two standing facts make that gap real:

- ADR 011's documented tradeoff: under the default `acceptEdits`
  permission mode the headless agent **cannot run tests or builds**, so
  its self-verification loop is weak unless the user opts into
  `bypassPermissions`. Even then, whether the agent verifies is up to the
  agent.
- docs/02's review bet ("does the stated intent match what the code
  does?") is strongest when mechanical failures are already filtered out —
  a reviewer's attention shouldn't be spent discovering that the tests
  don't pass.

User call (2026-07-17): after a prompt session fully executes, graphwerk
should run a **deterministic step** — a script, a make target, whatever
the repo uses — covering tests, validation, build. If it passes, control
goes back to the user. If it fails, re-trigger the agent with the failure
as additional context.

This is Phase 3 territory ("close the loop — reject drives the session")
pulled forward, with precedent: ADR 011 pulled the prompt box forward the
same way. The mechanism it needs — resuming the stored session with a
follow-up prompt — is exactly the machinery Phase 3's reject flow needs,
and `SessionRunner` already stores `_last_session_id` as deliberate
groundwork for it. The check gate delivers that machinery with a
*deterministic* trigger first; the human reject flow will reuse it.

## Decision

Graphwerk's orchestration grows one loop: **session → check → (on
failure) bounded auto-resume → … → hand over**.

1. **`CheckRunner`** (new, `graphwerk/check.py`): owns at most one check
   subprocess. Starts the configured shell command with the staged root
   as working directory, non-blocking (`Popen`), settled by status polls
   under a lock — the same poll-driven pattern `SessionRunner` uses
   (ticket 086). Result: exit code plus a bounded tail of combined
   output (the last ~100 lines / few KB — enough context for a re-prompt,
   never the whole log). A command that cannot launch (`OSError`) settles
   as a distinct terminal failure.
2. **`SessionRunner.resume(prompt)`** (`graphwerk/session.py`): spawns
   `claude -p <prompt> --resume <last_session_id>` with the same flags,
   output handling, and one-child-at-a-time semantics as `start`. Errors
   if no session id is stored or a child is running.
3. **`SessionCycle`** (new, `graphwerk/cycle.py`): the state machine
   gluing them, advanced by status polls like everything else:
   `running → checking → done` on a passing check;
   `checking → resuming(n) → running → checking …` on failure while
   attempts remain; `checking → check_failed` when attempts are
   exhausted (or the check command itself can't launch — retrying the
   agent won't fix a bad command). The failure re-prompt is a fixed
   template carrying the command, exit code, and output tail, and asks
   the agent to fix the failures (session guidance still applies via the
   existing `--append-system-prompt`). A session that itself fails ends
   the cycle without checking. Retry cap defaults to **1** automatic fix
   attempt.
4. **Configuration**: `--check "<command>"` on `serve`/`start` — opt-in;
   without it, behavior is exactly today's. `--check-retries N` adjusts
   the cap. No config file yet: one command string is the smallest
   coherent surface, and it composes (point it at `make check`, a script,
   `pytest`).
5. **API/UI**: `/api/session` reports the cycle's state (including
   `checking` / `resuming` / `check_failed`), the attempt count, and the
   last check's exit code + output tail. The prompt bar stays disabled
   for the whole cycle — "hand control back to the user" is literally
   when the bar re-enables — with the busy indicator naming the phase.
   A failed gate shows a banner with the output tail; the user reviews
   anyway, knowing what's broken. Render-only JS, per ADR 005.

## Alternatives considered

- **Have the agent verify itself** (`bypassPermissions` + guidance text
  telling it to run the tests) — nondeterministic by construction: the
  agent may skip, misread, or under-run the suite, and it requires
  weakening the conservative permission default on a LAN-exposed
  endpoint. The whole point of the user's ask is a step the agent cannot
  skip. Rejected.
- **Claude Code Stop hook inside the worktree** runs the check and blocks
  the session from stopping until it passes — keeps the loop invisible
  inside the session: graphwerk can't bound the retries, can't surface
  check state in the UI, and the config would live in per-worktree Claude
  settings graphwerk would have to write. The orchestrator architecture
  (docs/03, ADR 011) puts this loop in graphwerk. Rejected.
- **Config file (`graphwerk.toml`) or make-target convention** instead of
  a flag — a new config surface (or an imposed build tool) to carry one
  string. A flag is the smallest step; a config file becomes worth it
  when flags multiply. Deferred, not rejected.

## Consequences

- Sessions get deterministic verification **without** weakening the
  `acceptEdits` default: the agent edits, graphwerk verifies. This
  directly compensates ADR 011's "self-verification is weaker" tradeoff.
- Review starts from a known-good (or known-bad, loudly) worktree — the
  reviewer's attention goes to intent, not to discovering broken tests.
- The server's process-management state grows from one child to a small
  state machine; contained in `SessionCycle` so `serve` stays stateless
  everywhere else.
- Failed checks consume extra agent turns (cost, latency) — bounded by
  the retry cap, default 1.
- The check command executes on the host, but it is operator-configured
  at launch, not client-supplied — unlike `/api/prompt` it adds no new
  remote-execution surface.
- Phase 3's reject flow gets `resume()` for free when it arrives.
- No invariant touched: the check runs in the agent's real worktree
  (observing, never intercepting writes); stdlib `subprocess` only;
  differ/models untouched; JS stays a thin consumer.

## Out of scope

- Reject → re-prompt UI flow (Phase 3 proper; reuses `resume()`).
- Gating sessions started outside graphwerk (external terminal) — the
  cycle wraps only sessions graphwerk spawned; watching for foreign
  session completion is its own problem.
- Parsing check output into per-node graph annotations (mapping a test
  failure to the symbol it exercises) — genuinely attractive, belongs in
  a later phase once the plain gate proves out; noted for the roadmap.
- Streaming check output to the UI (same no-transcript stance as
  ADR 011; the bounded tail after the fact is the product surface).
- A config file for check settings — see Alternatives.
