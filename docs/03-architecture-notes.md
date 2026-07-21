# Architecture Notes

Design analysis for the concept in [02-product-concept.md](02-product-concept.md).

## The trap: intercepting writes breaks the agent

The naive design — an MCP server that absorbs Claude's `Edit`/`Write` calls so they never hit disk — breaks Claude Code's working loop. The agent assumes its edits are real:

- It reads back files it just modified and makes further edits on top.
- It runs builds and tests against the edited files and iterates on failures.

If writes are silently staged elsewhere, the agent's next read returns stale content, multi-step edits stack incoherently, and nothing can be verified. The result is *worse changes* arriving at the review layer. Any design must keep the agent's feedback loop intact.

## The fix (v1–Phase 3): shadow workspace (git worktree) — retired by ADR 058

v1 through Phase 3 let Claude work in a real but isolated copy of the repo
— a **git worktree** (first-class in Claude Code) — so the agent operated
at full capability (real files, real builds, real test runs) while the
graph app treated the delta between the worktree and the developer's
branch as an unlanded staging area, applied node by node.

**ADR 058 retires this.** Walking through what that isolation actually
bought (docs/02, product concept) against what it cost (a second
directory to manage, and an unsolved "base moved under staged" conflict
problem it created) concluded the isolation was mostly protecting
graphwerk's own apply/commit engine, not the developer. Removing the
apply/commit engine (below) removes the reason to keep the second
directory too. Claude now works directly in the developer's one working
directory, exactly as a stock Claude Code session does — from a console
invocation or the graph app's prompt box.

The graph app instead treats the *delta between the working directory and
the git ref it started from* as the change set to review:

1. **Watch** the working directory for file changes (fs events).
2. **Diff** the working directory vs. the recorded base ref (`git show
   <ref>:<path>` for base content — no second checkout needed).
3. **Map hunks to symbols** with tree-sitter → each changed class/function
   becomes a colored node (green = modified, blue = new, red = deleted,
   yellow = affected caller; ADR 030).
4. **Land** = the developer's own plain `git commit` (or `git stash`/
   `checkout`/`reset` to undo) — graphwerk performs no write of its own.

**Fallback/secondary mechanism:** Claude Code PreToolUse hooks *can* intercept and deny `Edit`/`Write` and forward payloads — useful as a signaling channel (e.g., notifying the graph app in real time which tool calls happen), but not as the place changes live.

## Re-triggering parts of a prompt

Telling the agent a specific change is wrong becomes a follow-up message **in the same Claude session**, so the agent keeps its context:

> "The change to `PaymentService` breaks the retry logic because X — redo just that part."

Shipped as the prompt box (ADR 011): the developer types this straight into the graph app, which sends it to the same running session via `SessionRunner`/`SessionCycle`. A structured per-node "reject" affordance existed briefly in v1 and was removed (ADR 057) once the free-form prompt box covered the same need without a redundant second control.

This requires programmatic session control, which nudges the architecture from "passive MCP sidecar" toward **"the graph app is the orchestrator"**:

- **Claude Agent SDK** — persistent, steerable sessions; the clean option.
- `claude --resume <session>` — shell-out alternative if the developer keeps their own terminal.

The developer can still type prompts in a terminal; the app only needs the ability to inject feedback into the session.

## Capturing the "why" per change

Each changed node should carry the rationale for its change. Three capture mechanisms, in order of preference:

1. **Mine the session transcript (primary).** Claude Code persists every session as JSONL (`~/.claude/projects/...`), with assistant narration interleaved with tool calls. The text immediately preceding an `Edit`/`Write` call is, in practice, the rationale ("Now adding retry handling to `PaymentService` so timeouts don't drop orders"). The graph app parses the transcript, matches each edit tool call to its symbol (via the file path + hunk mapping), and attaches the preceding narration to that node. Zero prompt overhead; works with a stock Claude session.
2. **Post-hoc summarization (cleanup pass).** Once the change set stabilizes, ask the same session — or a cheap model (Haiku) — for a one-sentence "why" per changed symbol. Produces uniform, reviewer-friendly explanations; the transcript narration remains available as the detailed view.
3. **Explicit annotation tool (fallback).** An MCP tool `explain_change(symbol, reason)` the agent is instructed to call. Most structured, but taxes the agent and it can forget; use only if transcript mining proves too noisy.

Caveats: one edit can serve multiple intents (refactor + fix), and narration quality varies — treat rationale as review *assistance*, never as verified truth. The rationale also feeds the rejection flow: "you said X, but the code does Y" is a sharper re-prompt than "redo this."

## The two hard problems (retired as apply problems by ADR 058)

These were framed as apply-engine problems through Phase 3; ADR 058
removes the apply engine, so neither is graphwerk's problem to solve
anymore — recorded here for history:

1. **Partial apply within a file.** Two changed methods in one class
   render as separate nodes, but their hunks can overlap or share context
   lines — applying one without the other would need careful hunk
   surgery. Moot once there's no apply operation; a partial land is just
   whatever the developer chooses to `git add -p`/commit themselves.
2. **Change interdependence.** A new `PaymentValidator` class is useless
   without the call-site change in `CheckoutService` that uses it. The
   graph still draws this as a **dependency edge between changed nodes**
   (still valuable to *see*), but there's no "apply group" action to
   offer — the developer commits both, or neither, with their own git.

## Proposed stack

| Concern | Choice | Why |
|---|---|---|
| Isolation | none — the developer's working directory | ADR 058: agent works in the real repo; delta is against a recorded base ref, not a second tree |
| Parsing / symbol mapping | tree-sitter | Broad language coverage, fast incremental parsing |
| Graph rendering | Cytoscape.js | Compound nodes (file ⊃ class ⊃ function) natively |
| Agent control | Claude Agent SDK | Persistent sessions for targeted re-prompting |
| Change signaling (optional) | Claude Code PreToolUse hooks / MCP | Real-time awareness of agent activity |
| Change rationale | Session transcript (JSONL) mining + Haiku summarization | Per-node "why" with no prompt overhead |

## Minimal prototype (validate before investing)

Goal: test whether the graph is actually a better review surface than a diff, *before* building apply semantics.

1. Create a worktree; let Claude Code make a multi-file change in it.
2. A watcher diffs worktree vs. base on every save and maps hunks to symbols via tree-sitter.
3. A static Cytoscape.js page renders the codebase graph with red/blue/grey coloring; clicking a node shows its diff plus the "why" mined from the session transcript.
4. **No apply button yet.** If reviewing on the graph doesn't beat reading the diff, stop there.

Phase 2 (if validated): file-level apply via `git checkout <worktree> -- <file>` equivalents → hunk-level apply → change-dependency edges → SDK-driven re-prompting.

*(Historical: this is the worktree-based path v1 through Phase 3 actually built. ADR 058 retires the worktree and the apply engine described above; see "The fix" section earlier in this doc for the current model.)*
