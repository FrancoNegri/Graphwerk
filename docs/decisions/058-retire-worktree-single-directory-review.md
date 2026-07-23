# 058. Retire the shadow worktree: graphwerk becomes a single-directory review lens over git

Status: proposed
Date: 2026-07-21
Supersedes: 037, 050

## Context

Managing two directories — the developer's repo and the shadow worktree
Claude actually edits — is awkward in practice: invoking Claude from a
console means remembering which directory to `cd` into, and invoking it
from the UI (ADR 011's prompt box) only papers over that by hiding the
`cd`, not by removing the second tree. The user experience this decision
targets is simple: call Claude from the console or the UI, and have it
touch the one repo you actually work in.

The worktree wasn't arbitrary — docs/03 adopted it to solve two real
problems: (1) "the trap," an MCP-style write interceptor breaks Claude
Code's read-your-own-writes loop, and (2) unreviewed changes should not
land in the developer's tree before the developer has looked at them. But
walking through what "review before apply" actually buys over plain git
(this session's discussion) surfaces that the second problem is mostly a
problem *graphwerk's own apply/discard engine* created, not one inherent to
Claude editing a real tree. Concretely, the still-unresolved question that
triggered this ADR — "what happens when the developer changes something in
`main` while the worktree has staged changes?" — has no answer today (it's
Phase 4's undone "conflict detection: warn when the base file moved under a
staged change," docs/04). If graphwerk instead treated the reviewed branch
as an ordinary git branch and left landing it to an ordinary `git merge` /
`git rebase`, that question stops being graphwerk's to answer — git already
owns branch-diverged-from-base conflict resolution, and reinventing it
inside the apply engine was never going to beat it.

ADR 050 (proposed 2026-07-20, the day before this one) fixed a real bug in
the previous apply/commit split (an approved-then-orphaned file could
silently never get committed) by introducing `ApprovalStore` as an
in-memory bookkeeping layer between "reviewer approves a node" and "file
actually gets written." That fix is superseded here, not because it was
wrong — it correctly solved the bug it targeted — but because this
decision removes the thing it was bookkeeping for: once graphwerk no
longer performs any file mutation (no `apply_file`, no `commit_all`
scoped copy), there's nothing left for an approval store to guard.

This is a real narrowing of docs/02's product concept, not a pure
implementation detail: step 3 ("land in a staging layer"), step 6
("applying changes node by node"), and step 7 ("reject re-triggers a
scoped follow-up") all describe graphwerk as the thing that performs
landing. After this decision it isn't. What survives, and is still
genuinely useful per this session's own review of "what does git not
give you": the symbol-level structural diff, blast radius, per-node
rationale, and change-dependency edges. None of those require graphwerk to
own the write path — they're a lens over a git-diffable set of changes,
which a plain working directory is.

## Decision

1. **No more shadow worktree.** `graphwerk start` no longer creates a
   second checkout. Claude — from a console `claude` invocation or the
   UI's prompt box — operates directly in the developer's one working
   directory, exactly as a stock Claude Code session does. `ShadowWorkspace`
   (`graphwerk/staging/workspace.py`) and its `git worktree add`/`remove`
   calls are deleted.

2. **"Base" becomes a git ref, not a second directory.** The differ's
   `base_root`/`staged_root` two-path model (`GraphService`,
   `ChangeSetBuilder` in `graphwerk/service.py`) becomes one working
   directory plus a base ref (default: the commit `HEAD` was at when the
   review session started). Base file content is read via git plumbing
   (`git show <ref>:<path>`) instead of a second tree walk; staged content
   is simply what's on disk right now. The symbol-diff logic itself
   (parse both texts, compare by qualified name) is unchanged — only where
   the two texts come from changes.

3. **Graphwerk stops mutating files, at all.** Delete `ApplyEngine`
   (`graphwerk/apply.py`), `ApprovalStore` (`graphwerk/approval.py`),
   `CommitEngine` (`graphwerk/commit.py`), and the discard engine
   (`graphwerk/discard.py`), along with `/api/apply`, `/api/unapprove`,
   `/api/commit`, `/api/discard`, and `/api/reject` from `graphwerk/
   server.py`. `GraphNode.approved` is dropped from the snapshot payload
   (`graphwerk/models.py`). Landing a reviewed change — or undoing one —
   is the developer's own plain git operation (`git commit`, `git stash`,
   `git checkout`, `git reset`) outside graphwerk, on their own branch.

4. **The prompt box, session runner, and check-gate machinery are
   unaffected in kind, only in *where* they operate.** `SessionRunner`
   (`graphwerk/session.py`), `SessionCycle` (`graphwerk/cycle.py`), and
   `CheckRunner` (`graphwerk/check.py`) spawn/resume Claude and run the
   configured check command in the developer's one working directory
   instead of a worktree path. Design-mode dialogue (ADR 047) is likewise
   unaffected — it never depended on the worktree.

5. **Rationale mining is unaffected.** Transcript discovery and mention
   attribution (ADR 006, 025-027) read the session JSONL regardless of
   which directory the session ran in; nothing there assumed a worktree
   path beyond "the directory the session was spawned in," which still
   exists (it's just the same directory now).

6. **Change-dependency edges stay, as a visual-only feature.** The graph
   can still draw an edge between two staged changes that reference each
   other and say so — it just no longer offers an "apply group" action,
   because there is no apply action of any granularity anymore.

## Alternatives considered

- **Keep the worktree, drop only ADR 050's approval bookkeeping** —
  smaller change, but leaves the two-directory friction that motivated
  this decision untouched, and still leaves "base moved under staged"
  unsolved. Rejected: doesn't address the actual complaint.
- **Keep the worktree and the apply engine, build the Phase 4 conflict
  detector instead** — directly answers "what if main changes while
  staging has changes," but by reinventing a worse version of `git merge`
  conflict resolution inside graphwerk's own engine. Rejected: more
  complexity, not less, and git already solves this well.
- **Make the worktree opt-in (a flag), keep both code paths** — preserves
  a disposable/exploratory-session workflow (throw away a whole attempt
  with zero risk to the main tree) for later. Rejected for now: two
  parallel implementations of "where does the agent write" is more
  surface than the current phase needs; noted below as a real, deferred
  idea rather than dropped outright.

## Consequences

- **Supersedes ADR 037** (commit/discard engine) **and ADR 050**
  (approval-scoped commit) in full — both describe machinery this
  decision deletes.
- **Resolves ADR 057's open question** ("Phase 3 decides whether to
  repurpose `/api/reject` or delete it") — deleted, along with `/api/apply`,
  `/api/unapprove`, `/api/discard`, `/api/commit`. There is no node-level
  land/revert action left to wire a reject button into.
- **Removes Phase 4's "conflict detection" item entirely** (docs/04) — not
  solved, made moot. A diverged base is an ordinary git-branch situation,
  resolved with ordinary git.
- **Removes docs/03's "two hard problems"** (partial apply within a file,
  change interdependence as an apply-group action) as engineering problems
  graphwerk must solve — there is no apply operation for them to be hard
  *for*. Change-dependency edges survive as information, not as a button.
- **Two behavioral caveats become the developer's own discipline, not
  graphwerk's problem to prevent:** don't run your own build/tests in the
  same directory while a session is actively working there (build/test
  interference); don't hand-edit a file while a session is actively
  editing it (rationale attribution may blend the two). Both are the same
  discipline as not having two people edit one repo uncoordinated at once.
- `CLAUDE.md`'s architecture invariant "the agent must keep a real
  filesystem to work in (git worktree)" needs rewording — the agent still
  gets a real filesystem (unchanged requirement), it's just the
  developer's own directory rather than an isolated copy. Updated in this
  pass.
- `docs/02-product-concept.md` steps 3, 6, 7 and the "apply group" bullet
  need rewording to drop the staging-layer/node-apply/reject-as-revert
  framing. Updated in this pass.
- `docs/03-architecture-notes.md`'s "the fix: shadow workspace" and "the
  two hard problems" sections are retired; "capturing the why," "graph
  rendering," and "re-triggering parts of a prompt via the prompt bar"
  sections are otherwise unaffected. Updated in this pass.
- No invariant conflict on stack: Python-everywhere/JS-only-in-static,
  minimal backend deps, and the `FileIndex`/`SymbolInfo` language-neutral
  contract are all untouched — this decision only changes where "base" and
  "staged" content come from, not how they're parsed or diffed.

## Out of scope

- An opt-in worktree mode for disposable/exploratory sessions (try three
  approaches, throw away the ones you don't like, zero risk to the real
  tree) — a real idea, deferred rather than dropped; would need its own
  ADR if picked up later, since it reintroduces a second code path for
  "where does the agent write."
- Any graphwerk-side git conflict UI or merge assistance — plain git
  handles this; nothing to build.
- `git push` after a developer's own commit — unrelated decision, already
  out of scope in ADR 050 for the same reason (leaves the local machine).
- Rewriting rationale-mining internals (transcript parsing, mention
  attribution) — unaffected by this decision beyond the directory the
  session happens to run in.
