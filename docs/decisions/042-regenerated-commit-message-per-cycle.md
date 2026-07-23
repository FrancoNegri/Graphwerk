# 042. Commit message regenerated from the full diff after every session cycle

Status: proposed
Date: 2026-07-17
Supersedes: 037

## Context

ADR 037 gave the session bar a commit-message box, filled by mining a
`Commit-message: <line>` the agent is instructed (`SESSION_GUIDANCE`) to
close its final transcript segment with. Dogfooding it surfaced two gaps,
both rooted in the same fact: nothing about the mined message is retained
anywhere durable.

- `RationaleStore.commit_message` is recomputed from scratch on every
  `/api/graph` call, always reading only `segments[-1]` of *whichever*
  transcript `find_latest_transcript` currently considers newest
  (`graphwerk/rationale/attribution.py:79`, `graphwerk/rationale/miner.py:89`).
  The box-fill guard that stops routine polling from clobbering reviewer
  edits (`completedSessionId` / `filledForSessionId` in `static/app.js`) is
  plain JS state — a page reload zeroes it, so the box comes back empty
  even though `meta.commit_message` is still being served.
- A second prompt spawns a brand-new `claude -p` session with its own
  transcript (`SessionRunner.start`, `graphwerk/session.py:37` — no
  `--resume`), so the first session's closing line is not superseded, it's
  gone: `find_latest_transcript` now points at the new file entirely.

This blocks Phase 2's exit criterion (docs/04): the dogfood loop is
supposed to *close* — prompt → review → commit — and today a multi-turn
review (issue a prompt, look at the graph, issue a follow-up prompt to fix
something) can't produce one coherent commit message covering everything
that happened, because the mechanism only ever remembers the most recent
session's own narration of itself.

## Decision

Replace transcript mining with an explicit, dedicated regeneration step
that reads the *whole current diff* — not any one session's transcript —
every time a session cycle finishes.

1. **`CommitMessageRunner`** (new, `graphwerk/commit_message.py`): given the
   current change set's diffs, spawns one headless, stateless
   `claude -p <prompt>` call (a cheap/fast model — Haiku, per the
   post-hoc-summarization option docs/03 already flagged for this exact
   job) asking for a single-line conventional-commit summary of the whole
   diff, and polls it to completion the same way `CheckRunner`/
   `SessionRunner` already do. No `--resume`, no file-editing permissions —
   it only reads text and returns text.

2. **`SessionCycle` gains a `summarizing` phase.** Today's chain is
   `running → checking → done` (or `→ check_failed`, or
   `→ resuming → running` again). This inserts one more link: once the
   check settles (pass or fail), the cycle spawns `CommitMessageRunner`
   over the *current* diff and stays in `summarizing` until it settles,
   before reporting `done`/`check_failed`. The generated message is held
   as instance state on the cycle (parallel to `check_exit_code`/
   `check_tail`) and returned from `status()` as `commit_message` — so it
   is server-held, and a browser reload just re-polls `/api/session` and
   gets the same value back. This is what actually fixes the reload bug;
   nothing client-side needs to remember anything across a reload anymore.
   If regeneration itself fails (bad binary, network), the cycle still
   reaches `done`/`check_failed` normally with whatever `commit_message`
   it already had (or `null` on the very first turn) — a failed
   regeneration must never block committing; typing a message by hand
   stays the fallback, per ADR 037.

3. **A second prompt doesn't lose the first message — it's superseded by
   construction.** `start()` leaves the held `commit_message` untouched
   while the new session/check/summarize chain runs (so the box still
   shows the last-known-good message throughout), and only overwrites it
   once *this* cycle's own regeneration settles — over the full diff as it
   stands *now*, which necessarily reflects everything both turns did.
   There is no merging logic because there are no separate messages to
   merge; there is one message, always describing the whole staged change
   set as of the last completed turn.

4. **Frontend**: the box fills from `session.commit_message` (`/api/session`)
   instead of `meta.commit_message`; `summarizing` joins
   `SESSION_BUSY_STATES` with its own label ("writing commit message…") so
   prompt/commit/discard stay disabled until the message is actually ready
   — no window where the reviewer can commit against a stale/empty box.
   The client-side `completedSessionId`/`filledForSessionId`/
   `minedCommitMessage` machinery in `static/app.js` goes away; the guard
   it existed for (never clobber an in-progress reviewer edit) is now
   equivalent to "only overwrite when the polled `commit_message` value
   actually changes," which needs no session-id bookkeeping.

This supersedes ADR 037's mining mechanism outright: the `Commit-message:`
line instruction in `SESSION_GUIDANCE`, `parse_commit_message`,
`RationaleStore.commit_message`, and its `meta["commit_message"]` snapshot
wiring (tickets 095/096) are removed, not kept alongside the new path.

## Alternatives considered

- **Keep mining the transcript, just persist it server-side to fix
  reload** — cheaper (no extra subprocess call) and would genuinely fix
  the reload half of the bug, but each mined line still only narrates its
  *own* session; a second prompt's line still can't describe the first
  prompt's work without new merge logic that has to guess how to combine
  two unrelated one-liners into one coherent conventional-commit summary.
  Explicitly not what was asked for (a message that "takes into account
  all changes").
- **Deterministic message built from diff stats** (files touched/added/
  deleted counts, maybe rationale bullets) — zero latency, zero cost,
  trivially reload-safe, but produces a mechanical bullet-dump, not a
  commit-quality summary. ADR 037 already rejected this shape once for
  the same reason.
- **On-demand regeneration (a button)** — cheaper on average (skips
  regeneration when the reviewer already knows what they want to type),
  but reintroduces an empty-by-default box as the common case and was
  already flagged as a bigger UI addition in ADR 037's own out-of-scope
  list. The user's call this round: fully automatic, right after every
  cycle, so the box is always populated by the time anyone looks.

## Consequences

- Fixes both reported bugs: reload-safe (server holds the value) and
  second-prompt-safe (regeneration covers everything, nothing to lose).
- One more headless `claude` call per prompt (latency + tokens), paid
  during `summarizing`, before control hands back — mitigated by using a
  cheap/fast model, and by it running after the reviewer's own check gate
  already has them waiting.
- `SessionCycle`'s state machine grows one more link; `TERMINAL_STATES`
  stays `(idle, done, failed, check_failed)` unchanged — `summarizing` is
  transient like `checking`/`resuming`, so no API consumer needs to learn
  a new terminal state, only one more busy-state label.
- Removes tickets 095/096's mechanism entirely (guidance line, parser,
  `RationaleStore.commit_message`, snapshot field) — dead code to delete,
  not deprecate in place, per CLAUDE.md's no-compat-shims stance.
- No new backend dependency (stdlib `subprocess`, same pattern as
  `SessionRunner`/`CheckRunner`); logic stays in Python, `app.js` only
  reads one more field off the existing `/api/session` poll.
- Invariants: none violated. This is a read-only, out-of-band informational
  call over the diff — it never touches the agent's own worktree session
  or its feedback loop (the "trap" in docs/03 is about intercepting the
  agent's *own* writes; this is a separate, stateless side call).

## Out of scope

- Bounding/truncating very large diffs fed into the regeneration prompt —
  fine at today's dogfood/mid-size scale (docs/04's Flask run); revisit if
  a real repo's diff blows the prompt budget.
- A manual "regenerate" button/retrigger — automatic-only per this
  decision; add later only if the automatic call needs a manual redo path
  (e.g. after it fails).
- Persisting the message (or any cycle state) across a `graphwerk serve`
  restart — stays in-memory only, same lifetime as `SessionRunner`/
  `SessionCycle` today, consistent with the roadmap's "no persistence
  beyond the filesystem, not now."
- A visible log of past prompts this cycle — considered and declined; the
  regenerated message is the whole feature, not a supplement to a prompt
  history.
- Model/timeout configuration surface for the regeneration call — a
  ticket-level default choice (e.g. Haiku), not an architectural fork.
