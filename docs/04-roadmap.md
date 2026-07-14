# Roadmap (drafted July 2026, after v1 experience prototype)

v1 proved the review surface: graph staging area, node states, per-change "why",
file-level apply, reject-as-re-prompt payload. What follows, in proposed order.

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

## Phase 3 — Close the loop (reject drives the session)

Goal: the reject button actually re-prompts the live agent.

- Session control via the Claude Agent SDK (or `claude -p --resume <session>`
  as the thin first cut): reject sends the recorded payload into the session.
- Agent activity indicator in the UI (idle / working / waiting on permission),
  fed by transcript tailing or hooks.
- Prompt box in the UI so the whole flow (ask → watch graph fill in → review →
  apply/reject) happens in one place.

## Phase 4 — Apply semantics (the hard problems)

Goal: graduate from file-level apply.

- Symbol-level apply: reconstruct the base file with only the selected
  symbol's change (the differ already works symbol-by-symbol; the writer is
  the new part). Fall back to file-level on overlap.
- Change-dependency edges: staged changes that reference each other's symbols
  get explicit edges + "apply group" (killer feature from the concept doc).
- Conflict detection: warn when the base file moved under a staged change.

## Phase 5 — Breadth and polish

- Multi-language indexing via tree-sitter (JS/TS first), behind the existing
  FileIndex contract.
- Rationale quality: post-hoc one-liner summarization pass (Haiku) over mined
  narration. **Dogfood finding (ticket 007, July 2026): this is needed sooner
  than "polish".** Current sessions batch many edits after one short lead-in
  sentence, so the "narration immediately before the edit" heuristic attached
  the same weak line to all six changed files — while the genuinely useful
  per-file rationale sat in the session's final summary, which the miner
  ignores. Any redesign (mine the wrap-up summary, attribute per-file
  mentions, summarize) is a `north-star` decision, not a quick fix.
- Packaging: `pipx install graphwerk`, static assets bundled into the package.
- Multi-session: several agents staging into one graph, per-session coloring.

## Deliberately not now

- Auth / remote deployment (localhost, LAN-by-flag stays the model for a while)
- Persistence beyond the filesystem (no DB until the graph outgrows recompute)
- VS Code embedding
