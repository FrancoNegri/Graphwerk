# 050. Apply becomes approval; commit is scoped to approved files

Status: proposed
Date: 2026-07-20

## Context

Two flows currently exist for landing a staged change, and they don't agree
with each other. Per-node apply (`ApplyEngine.apply_file`, v1) copies one
staged file over the base file immediately, no git involved — the sidebar's
"Apply file X" button. Commit-all (`CommitEngine.commit_all`, ADR 037)
re-diffs the *entire* staged-vs-base tree via `ChangeSetBuilder`, applies
every file that still differs, then `git add`+`git commit` scoped to those
paths.

Because commit-all recomputes the diff from scratch rather than tracking
what was already approved, using both flows together is broken: apply file
A individually → base now equals staged for A → A no longer appears in the
diff → the next commit's `git add` never touches it. A's change sits in the
base tree as an uncommitted, git-untracked modification indefinitely — the
one screen ADR 037 built specifically to close the loop (docs/04's Phase 2
exit criterion) silently fails to close it whenever per-node apply is used
first.

Node-level review is not incidental here — it's docs/02's core pitch
(structural context, blast radius, rationale *per node*) over a flat diff
viewer. So the fix isn't to drop node-level review, it's to stop treating
"I approve this node" and "write it to disk right now" as the same action.

## Decision

1. **`ApprovalStore`** (new, `graphwerk/approval.py`): in-memory
   approve/unapprove of rel_paths, server-lifetime like `SessionCycle`
   (ADR 042 precedent — no persistence beyond the running process). Each
   approval is stamped with the file's `file_fingerprint` (mtime_ns, size —
   the same idiom `ChangeSetBuilder`'s cache and `GraphService.state_hash`
   already use) at approval time; `is_approved` returns false if the
   staged file's current fingerprint no longer matches. This is the guard
   against silently committing content the reviewer never actually looked
   at: approve file A, then a follow-up prompt edits A again, and the stale
   approval evaporates on its own — no explicit invalidation call needed
   anywhere else in the codebase.

2. **`/api/apply` now marks approval, not a write.** The endpoint calls
   `approval_store.approve(path)` instead of `engine.apply_file(path)`.
   A new `/api/unapprove` lets the reviewer change their mind.
   `ApplyEngine.apply_file` keeps its existing behavior (copy staged→base)
   but is now only invoked from inside `CommitEngine.commit_all`, once per
   approved path, right before `git add`.

3. **`CommitEngine.commit_all` scopes to approved ∩ still-changed paths.**
   Raises `CommitError("nothing approved to commit")` when that
   intersection is empty. On success, clears the committed paths from
   `ApprovalStore` so the next review cycle starts clean. This is a real
   partial-commit capability — a review pass can approve 2 of 5 changed
   files and commit just those, leaving the rest staged.

4. **`/api/discard` clears the whole `ApprovalStore`.** Discard already
   reverts every staged change regardless of approval (unaffected by this
   ADR); once the underlying diff is gone, any leftover approval entries
   are moot and should not silently reappear if the same path changes again
   later.

5. **`/api/reject` unapproves the rejected path.** A node the reviewer just
   rejected should not ride along into the next commit because it happened
   to be approved earlier in the same cycle.

6. **`GraphNode.approved: bool`** joins the snapshot payload (file nodes
   only — approval stays file-granularity, matching `apply_file`'s existing
   scope). Sourced from `ApprovalStore` in `GraphService.snapshot()`, so a
   page reload reflects real approval state instead of client-held memory —
   same reload-safety fix ADR 042 already applied to the commit message.

7. **Frontend.** The sidebar's "Apply file X" button becomes an
   Approve/Unapprove toggle reflecting `node.approved`. The commit bar
   shows how many files are approved and disables the commit button at
   zero; discard is unaffected (still whole-set).

## Alternatives considered

- **Scrap per-node apply, keep commit-all only** — removes the conflict
  outright, but cuts the node-level accept action docs/02 treats as the
  product's actual differentiator over a diff viewer. Rejected.
- **Minimal fix: keep both as-is, teach commit-all's `git add` to also
  include paths applied since the last commit** — smallest change, fixes
  the bug, but leaves two conceptually separate "accept" actions in the UI
  with no shared meaning, which is the design smell, not just the bug.
  Patches a symptom.
- **Require full review before enabling commit (approval as a gate, not a
  selector)** — avoids partial-commit git plumbing entirely, but the
  reviewer explicitly asked for true partial commit; a gate-only design
  throws that away for no cost savings that matter at this scale.

## Consequences

- Fixes the orphaned-uncommitted-file bug: nothing is ever written to the
  base tree outside of `commit_all`, so nothing can fall out of the `git
  add` scope.
- Supersedes ADR 037's out-of-scope note that deferred partial commit to
  "Phase 4's apply-group work" — that note assumed apply-per-node already
  wrote to disk immediately ("already covers it"), which is exactly the
  assumption this ADR removes. Grouped/multi-select bulk approval in the UI
  is still out of scope, per-file approval is not.
- `ApplyEngine.apply_file`'s contract is unchanged; only its caller moves
  from the `/api/apply` endpoint to inside `CommitEngine`.
- No new backend dependency; git usage is unchanged from ADR 037 (still
  stdlib `subprocess`, still scoped `git add`).
- Invariants: none violated. The agent's own worktree session is untouched
  (approval is a reviewer-side bookkeeping concern); logic stays in Python;
  `app.js` only gains a toggle and a count, no new client-side state of
  record (mirrors ADR 042's "server holds the truth" fix).

## Out of scope

- Symbol/hunk-level approval — apply/approval stays file-granularity, same
  as today ("hunk-level apply is phase 2", `graphwerk/apply.py`); unchanged
  by this ADR.
- Grouped/multi-select bulk-approve UI — still deferred, now genuinely to a
  later phase rather than assumed-covered.
- `git push` after commit — a separate decision with its own blast-radius
  question (pushes leave the local machine and touch shared state); not
  folded into this one.
- Carrying approvals across a `graphwerk serve` restart — in-memory only,
  consistent with `SessionCycle`'s existing lifetime.
