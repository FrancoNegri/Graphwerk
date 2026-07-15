# 012. Rationale guidance injected into spawned sessions

Status: proposed
Date: 2026-07-15

## Context

Per-node rationale is a core concept feature (docs/02): review becomes "does
the stated intent match the code?". ADR 006 rebuilt the miner around
whole-transcript mention attribution, and it works — but the first prompt-box
dogfood run (agendabot, webhook.py split, 2026-07-15) showed the remaining
weakness is the **raw material**, not the attribution: the latest segment
mentioning a file was process narration ("Now I have a full picture,
including the test-coupling constraints... Let me create the new module
files."), because the session never produced a per-file wrap-up for
later-wins attribution to prefer.

ADR 006 anticipated this ("revisit if attribution quality proves
insufficient") and docs/03 always treated transcript mining's "zero prompt
overhead" as a preference, not a law. What changed since: ADR 011 made
graphwerk the process that **spawns** the session, so for the first time we
control what the agent is told — without taxing terminal-started sessions
or adding any dependency.

## Decision

Spawned sessions get a short standing instruction that shapes their narration
into what the miner already consumes:

1. **`graphwerk/rationale/guidance.py`** (new): a `SESSION_GUIDANCE` string
   constant asking the agent to end its work with a per-file summary — one
   line per changed file, naming the file path and key changed symbols, each
   stating *why* the change serves the request (not what it does). The
   wording contract is deliberate: file paths and symbol names as distinct
   tokens in a final summary is exactly the shape ADR 006's later-wins
   file/symbol attribution prefers. The text lives in `rationale/` because
   its wording is coupled to the miner's matching rules, not to process
   management.
2. **`SessionRunner` gains a `system_prompt` constructor parameter**
   (default empty): when non-empty, the child command gains
   `--append-system-prompt <text>`. `session.py` stays ignorant of the
   rationale layer — the string is injected by the caller.
3. **`cli._serve` wires `SESSION_GUIDANCE` into the runner** it already
   constructs. Terminal-started sessions are untouched and keep working via
   ADR 006's pipeline as before.
4. **A round-trip test pins the contract**: a synthetic transcript whose
   final message follows the guidance format must attribute a distinct
   rationale to each mentioned file/symbol through the real miner. If
   guidance wording and miner rules ever drift apart, this test fails.

## Alternatives considered

- **CLAUDE.md written into the staging worktree** — would also reach
  terminal sessions, but the file becomes part of the staged delta (an
  added node in the graph, noise in every review), needs cleanup logic,
  and edits the tree the agent owns. Rejected.
- **Post-hoc summarization pass (Haiku / `claude -p`)** — ADR 006 already
  weighed and deferred it: nondeterministic, costs tokens, resists pytest.
  Stays the Phase 5 fallback via the sidecar, unchanged.
- **Explicit `explain_change` annotation tool** — docs/03 ranks it last
  (taxes the agent, forgettable); guidance-shaped narration is lighter and
  degrades gracefully.
- **Tune attribution further instead** — the dogfood evidence shows the
  useful sentence often doesn't exist in the transcript at all; no
  attribution rule can pick what was never written.

## Consequences

- Spawned sessions spend a small amount of prompt/output budget on the
  summary — a deliberate trade of docs/03's "zero prompt overhead" for
  rationale quality, confined to sessions graphwerk starts.
- The agent may ignore or half-follow the guidance; the ADR 006 fallback
  chain (qualname → file → preceding-narration → nothing) is untouched, so
  quality degrades to today's behavior, never below it.
- Guidance wording is Python, unit-tested, and versioned with the miner it
  feeds (thin-JS rule holds; no new deps; worktree never touched).
- Groundwork for Phase 3: reject payloads quote rationale, so better raw
  material sharpens the reject loop too.

## Out of scope

- Any change to miner/attribution rules (ADR 006 stands).
- Summarization pass (Phase 5, sidecar integration point unchanged).
- Guidance for terminal-started sessions (would need docs, not code — a
  future README note at most).
- A CLI flag to customize/disable the guidance text — add only if dogfooding
  shows a need.
