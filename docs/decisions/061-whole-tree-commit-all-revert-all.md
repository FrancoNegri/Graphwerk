# 061. Whole-tree commit-all / revert-all: a narrow exception to ADR 058

Status: proposed
Date: 2026-07-22

## Context

ADR 058 (2026-07-21) retired every graphwerk-owned write path — no
`ApplyEngine`, `ApprovalStore`, `CommitEngine`, discard engine, no
`/api/apply|unapprove|commit|discard|reject` — on the grounds that
"landing/undoing a change is the developer's own plain git operation, not
a graphwerk endpoint" (CLAUDE.md). That decision was driven by two
concrete problems the old *node-level* apply engine created: partial apply
within a file (overlapping hunks across two changed methods) and change
interdependence (a new class useless without its call-site change, with no
clean "apply group" primitive). Neither problem is inherent to Claude
editing a real tree — they were both artifacts of offering apply at
symbol granularity.

The user now wants a convenience the developer would otherwise type by
hand every session: one button that stages and commits everything the
graph currently shows as changed, using the commit message graphwerk
already mines from the session transcript (`RationaleStore.commit_message`,
ADR 037/042, already surfaced as `snapshot.meta.commit_message`), and one
button that undoes it. This is a **whole-tree, all-or-nothing** operation —
there is no partial selection, so neither of ADR 058's stated hard
problems applies: nothing to reconstruct within a file, nothing to group.
It is also, mechanically, nothing more than the exact `git add`/`git
commit`/`git stash` invocations the ADR 058 model already expects the
developer to type themselves — this decision automates that typing for the
whole-tree case, not a reintroduction of symbol-level staging.

Phase 2's exit criterion (docs/04) is "build a graphwerk feature using
graphwerk to review it" — dogfooding the tool on itself. ADR 058 removed
every landing affordance in service of a real simplification, but the
practical effect during dogfooding is that every session ends with the
developer leaving the graph UI to type `git add -A && git commit -m
"..."` by hand. This closes that gap without reopening node-level apply.

## Decision

1. **Two new whole-tree write actions, gated to the live pair only.**
   Per ADR 060, a `(base, staged)` pair is "live" only when `staged`
   resolves to the working-directory token — that's the only pair with an
   actual working tree behind it. Both new actions 400 on any other pair,
   same posture ticket 175 already gives the prompt box.
   - **Commit-all:** `git add` exactly the rel paths the resolved pair's
     diff currently reports as `MODIFIED`/`ADDED`/`DELETED` (not `git add
     -A` — scoped to what the developer is actually reviewing, not
     whatever else happens to be dirty in their tree), then `git commit -m
     <message>`. `message` is an optional request-body override, else the
     pair's mined `commit_message`, else the request 400s — there's
     nothing to commit a message for.
   - **Revert-all:** `git stash push -u -- <same paths>`. Chosen over `git
     reset --hard` specifically for recoverability — `git stash pop`/`git
     stash list` beats reflog-only recovery as a safety net for a button
     click, per explicit user call.
2. **New module `graphwerk/landing.py`** — deliberately not reusing the
   deleted `apply.py`/`commit.py` names, because this isn't a resurrection
   of that engine's bookkeeping, just two `subprocess.run(["git", ...])`
   calls in the same style as `differ.py`'s existing `_git_ls_tree`/
   `_git_show_bytes` plumbing:
   - `commit_all(repo_root: Path, paths: list[str], message: str) -> None`
   - `revert_all(repo_root: Path, paths: list[str]) -> None`
   Empty `paths` is a no-op for both — never invoke `git` with no
   pathspec, which would silently operate on the whole tree.
3. **`GraphService.changed_paths() -> list[str]`** — the rel paths whose
   status is in the existing `CHANGED` set (`MODIFIED`/`ADDED`/`DELETED`),
   the same set `snapshot()` already uses to decide `why`/color. Reused by
   both new endpoints.
4. **Two endpoints in `server.py`:** `POST /api/commit-all` and `POST
   /api/revert-all`, accepting the same `base`/`staged` query params as
   `/api/graph` — they act on whatever pair the developer currently has
   selected, not a separate hidden notion of "the real" pair. Commit-all
   additionally accepts an optional JSON body `{"message": ...}`.
5. **Two buttons in the UI**, next to ticket 174's base/compare-to
   dropdowns, visible only when the selected `staged` is live (ticket
   175's existing gate). Commit-all prefills from the snapshot's
   `commit_message`. Revert-all confirms via `window.confirm()` before
   firing. Both refetch `/api/graph` immediately on success rather than
   waiting for the next hash poll.

## Alternatives considered

- **Resurrect ADR 058's `ApplyEngine`/`CommitEngine`/`ApprovalStore`
  wholesale** — rejected: that machinery solved node-level partial apply
  and approval bookkeeping, neither of which a whole-tree, all-or-nothing
  action needs. Reusing it would reintroduce exactly the complexity ADR
  058 removed, for a feature that doesn't require it.
- **`git reset --hard` for revert** — rejected per explicit user call:
  recoverability matters more than literal "revert to base," and
  reset --hard's reflog-only recovery is a worse safety net than `stash`.
- **`git add -A` (whole tree) for commit-all, ignoring the graph diff** —
  rejected per explicit user call: would silently commit unrelated dirty
  files outside the reviewed session — the same class of accidental-
  inclusion risk ADR 050 (superseded) originally patched with
  `ApprovalStore`, reappearing in a new form.
- **Stay plain-git-only: a footer showing copy-pasteable `git` commands,
  no backend write at all** — offered to the user as the ADR-058-
  preserving option; rejected in favor of the button per explicit user
  choice, given that neither of ADR 058's actual problems applies here.

## Consequences

- **Narrowly amends ADR 058's "graphwerk stops mutating files, at all."**
  Node-level apply, per-symbol staging, and approval bookkeeping remain
  retired — this decision does not reopen them, and does not restore
  `GraphNode.approved` or any partial-selection UI.
- `CLAUDE.md`'s architecture invariant line needs a note about this narrow
  exception. Updated in this pass.
- `docs/02-product-concept.md` step 7 needs the same note. Updated in this
  pass.
- `docs/04-roadmap.md` Phase 2 gets a bullet — this is dogfooding
  convenience in service of Phase 2's own exit criterion. Updated in this
  pass.
- Does not reopen Phase 4 (still retired) — no conflict detection, no
  hunk-level anything, no approval store, no per-node action.
- No stack-invariant conflict: git is invoked via `subprocess` (already
  the pattern in `differ.py`), no new backend dependency; JS stays thin
  (two buttons + confirm + refetch, no new JS logic of substance);
  `FileIndex`/`SymbolInfo` untouched.

## Out of scope

- Per-node/per-file commit or revert — still dead per ADR 058. This
  decision is deliberately all-or-nothing across a live pair's `CHANGED`
  files; a finer-grained action would need its own ADR since it reopens
  exactly the problems ADR 058 retired.
- `git push` after commit-all — same carve-out ADR 050/058 already made;
  stays local, unrelated decision.
- Handling `git commit`/`git stash` failure beyond surfacing git's own
  error (e.g. a commit hook rejects, or there's nothing to stash) as a
  plain HTTP error — no retry, no special-casing.
- Editing the mined commit message beyond a plain text override in the
  request body / UI field — no rich editor, no per-file messages.
- An opt-in worktree/disposable-session mode — already out of scope in
  ADR 058, unaffected by this decision.
