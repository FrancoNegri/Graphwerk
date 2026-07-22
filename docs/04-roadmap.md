# Roadmap (drafted July 2026, after v1 experience prototype)

v1 proved the review surface: graph staging area, node states, per-change "why",
file-level apply, reject-as-re-prompt payload. What follows, in proposed order.

**2026-07-21 (ADR 058):** the shadow-worktree isolation and the apply/
approval/commit/discard engine that Phase 2 and Phase 3 built below are
retired — graphwerk no longer stages or mutates files, and reviews the
developer's own working directory against a recorded base ref instead.
The bullets below are left as the historical record of what actually
shipped in those phases; Phase 4 (below) is where the retirement's
consequences are spelled out.

## Phase 2 — Real session, end to end (dogfooding) ← **NEXT (chosen July 2026)**

Goal: retire the scripted demo as the only path; review actual Claude Code work.
Exit criterion: **build a graphwerk feature using graphwerk to review it.**

- `graphwerk start`: one command that creates the shadow worktree, prints the
  `claude` invocation to run inside it (or launches it), and serves the UI.
- Transcript auto-discovery: find the session JSONL under `~/.claude/projects/`
  for the staged worktree instead of requiring `--transcript`.
- Real-repo hardening: run against this repo and at least one mid-size repo;
  fix what the differ/indexer trips on (symlinks, generated files, .gitignore
  respect). *Done — Flask run (959 nodes / 3632 edges): `/api/graph` ~1s,
  `/api/hash` ~30ms, so no snapshot perf work needed at mid-size. Two real
  trips filed as tickets 008 (unparseable staged file reads as mass-delete)
  and 009 (non-Python staged changes invisible in the graph).*
- Scale UX: collapse/expand file boxes (double-click), a "changed + blast
  radius only" view toggle so big repos open readable.
- Whole-tree "commit all" / "revert all" buttons, using the mined commit
  message, so a dogfooded session can be landed or undone without leaving
  the graph UI. *Added 2026-07-22 (user call): ADR 061, tickets 176-179 —
  a narrow, explicitly all-or-nothing exception to ADR 058's "graphwerk
  never mutates files"; node-level apply stays retired.*

## Phase 3 — Close the loop (reject drives the session)

Goal: the reject button actually re-prompts the live agent.

- Session control via the Claude Agent SDK (or `claude -p --resume <session>`
  as the thin first cut): reject sends the recorded payload into the session.
- Agent activity indicator in the UI (idle / working / waiting on permission),
  fed by transcript tailing or hooks.
- Prompt box in the UI so the whole flow (ask → watch graph fill in → review →
  apply/reject) happens in one place. *Pulled forward 2026-07-15 (user call):
  ADR 011, tickets 038-040 — kickoff-only, input box + status, no chat log;
  reject/resume stays here.*
- Deterministic post-session check gate: after a spawned session completes,
  run a configured check command (tests/build/lint) in the worktree; pass →
  hand control back, fail → auto-resume the session with the failure output,
  bounded retries. *Pulled forward 2026-07-17 (user call): ADR 040, tickets
  105-109 — this ships the `--resume` machinery the reject flow will reuse;
  the human reject → re-prompt UI stays here.*

## Phase 4 — Apply semantics — retired by ADR 058

*Retired 2026-07-21 (user call): ADR 058, tickets 157-162. The worktree,
the apply/approval/commit/discard engine (ADR 037, ADR 050), and the
node-level apply gesture are all removed — graphwerk stops mutating files
entirely and becomes a review lens over the developer's own git working
directory. Landing a change is the developer's own `git commit`; undoing
one is their own `git stash`/`checkout`/`reset`. This makes every goal
below moot rather than solved:*

- ~~Symbol-level apply: reconstruct the base file with only the selected
  symbol's change.~~ No apply operation exists to extend.
- Change-dependency edges: kept as a *visual* feature (still valuable to
  see two changes reference each other) — the "apply group" action is
  gone along with apply itself.
- ~~Conflict detection: warn when the base file moved under a staged
  change.~~ No longer graphwerk's problem — a diverged base is an
  ordinary git branch situation, resolved with ordinary `git merge`/
  `git rebase`.

## Phase 5 — Breadth and polish

- Multi-language indexing via tree-sitter (JS/TS first), behind the existing
  FileIndex contract. *Markdown pulled forward 2026-07-18 (user call): ADR
  046, tickets 124-128 — a stdlib heading-level extractor, not tree-sitter,
  because a product's decision knowledge base (ADRs/tickets/roadmap) is the
  first target, not general prose. Ships a second review domain (docs/02):
  the same graph/session/apply pipeline, pointed at documentation instead of
  code, plus a user-triggered "continue this session" control so a design
  dialogue can have real back-and-forth turns. Full JS/TS via tree-sitter
  stays here.*
- Rationale quality: post-hoc one-liner summarization pass (Haiku) over mined
  narration. **Dogfood finding (ticket 007, July 2026): this is needed sooner
  than "polish".** Current sessions batch many edits after one short lead-in
  sentence, so the "narration immediately before the edit" heuristic attached
  the same weak line to all six changed files — while the genuinely useful
  per-file rationale sat in the session's final summary, which the miner
  ignores. Any redesign (mine the wrap-up summary, attribute per-file
  mentions, summarize) is a `north-star` decision, not a quick fix.
  *Decided 2026-07-14: ADR 006 (whole-transcript mention attribution,
  deterministic; summarization stays here as the fallback), tickets 018-021.*
- Packaging: `pipx install graphwerk`, static assets bundled into the package.
- Multi-session: several agents staging into one graph, per-session coloring.

## Deliberately not now

- Auth / remote deployment (localhost, LAN-by-flag stays the model for a while)
- Persistence beyond the filesystem (no DB until the graph outgrows recompute)
- VS Code embedding
