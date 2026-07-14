# 001. Phase 2 — review a real Claude session end to end

Status: proposed
Date: 2026-07-14

## Context

v1 proved the review surface (docs/02) but only against the scripted demo.
The roadmap (docs/04) picks "Phase 2 — real session, end to end" as next:
retire the demo as the only path, with the exit criterion **build a graphwerk
feature using graphwerk to review it**. Four gaps stand between v1 and that:

1. Setup is manual — the user must create a worktree and pass `--base/--staged`
   by hand.
2. Rationale mining needs an explicit `--transcript` path, which the user has
   to dig out of `~/.claude/projects/` themselves.
3. The indexer/differ walk (`iter_python_files`) uses a hardcoded ignore list —
   real repos with .gitignored/generated files and symlinks will index junk.
4. A real repo's graph opens as an unreadable wall — no collapse, no way to
   see only the change and its blast radius.

## Decision

Ship Phase 2 as four narrow pieces, all inside existing layers:

1. **`graphwerk start`** — one command that ensures the shadow worktree
   (existing `ShadowWorkspace.ensure`), **prints** the `claude` invocation to
   run inside it (`cd <staging> && claude`), and serves the UI with
   base = the repo and staged = the worktree. It does **not** launch or drive
   the Claude session — the developer keeps their terminal (docs/02 open
   question, answered conservatively; session control is Phase 3).
   Default staging path: a sibling directory `<repo-name>-graphwerk-staging`.
2. **Transcript auto-discovery** — map the staged worktree path to its
   Claude Code project directory (`~/.claude/projects/<path with / and .
   replaced by ->`) and take the most recently modified `*.jsonl`.
   `RationaleStore.reload()` re-resolves on every reload, so a session started
   after `serve`/`start` is picked up automatically and a newer session wins.
   An explicit `--transcript` stays pinned and skips discovery.
3. **Git-aware file enumeration** — when a tree is git-managed, enumerate
   Python files via `git ls-files --cached --others --exclude-standard`
   (respects .gitignore for free) and skip symlinks; otherwise keep the
   current `rglob` walk so any plain directory pair still works. (The demo
   trees are in fact git repos — `demo.py` inits the base and stages via a
   worktree — so the demo exercises the git branch; the fallback's consumer
   is arbitrary non-git pairs passed to `serve`.) The differ, indexer, and
   `state_hash` all share this one walk, so they stay consistent.
4. **Scale UX, in `static/` only** — (a) double-click collapses/expands a
   file's compound node; (b) a "changed + blast radius only" toggle that
   hides unchanged, unaffected nodes and the edges into them. Any Cytoscape
   plugin needed is vendored via npm into `static/vendor/`, never CDN.

The phase exit (dogfood: implement a graphwerk ticket inside the staging
worktree and review/apply it through the UI) runs after these land, as its
own validation ticket.

## Alternatives considered

- **`start` launches the `claude` process itself** — couples graphwerk to
  terminal/PTY management and drifts into Phase 3 (session control) before
  the review loop is proven on real sessions. Printing the command gets the
  same end-to-end flow with zero orchestration risk.
- **Transcript discovery watches/merges all sessions for the worktree** —
  merging narration across sessions needs ordering and conflict rules we
  have no evidence we need; latest-by-mtime re-checked each reload covers
  the one-agent dogfooding case. Multi-session is explicitly Phase 5.
- **Hand-rolled .gitignore parsing (stdlib)** — reimplements git semantics
  (nested ignores, negations) badly; `git ls-files` is exact and git is
  already required for worktrees. The non-git fallback keeps the differ's
  "any directory pair" property for the demo.
- **Server-side graph filtering for scale UX** — pushes view state into the
  API and couples server to presentation. The snapshot is already small
  enough to ship whole; hiding is a client concern.

## Consequences

- Easier: real-session review becomes one command; dogfooding (the exit
  criterion) becomes possible; big repos open readable.
- Harder/new: `iter_python_files` grows a git/non-git branch — the walk
  becomes the one place enumeration semantics live, and its tests matter
  more. Discovery depends on Claude Code's `~/.claude/projects` path-munging
  convention (undocumented; isolate it in one function so a format change is
  a one-line fix).
- Invariants: none changed. The worktree invariant is reinforced; no new
  backend deps; JS stays in `static/`.

## Out of scope

- Launching/steering the Claude session, reject-triggered re-prompting,
  agent activity indicator, prompt box in the UI — Phase 3.
- Symbol-level apply, change-dependency edges, conflict detection — Phase 4.
- Multi-session staging, tree-sitter languages, Haiku summarization,
  packaging — Phase 5.
- Snapshot/state-hash performance work for very large repos — only if the
  mid-size dogfood run shows it's needed (file findings in the roadmap).
