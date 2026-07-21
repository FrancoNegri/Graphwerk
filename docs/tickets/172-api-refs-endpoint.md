# 172. `GET /api/refs` endpoint

Status: done
Decision: docs/decisions/060-comparison-picker-any-ref-vs-any-ref.md

## Goal

Give the frontend something to populate the comparison dropdowns with:
branches, tags, and the most recent commits on the current branch, plus
the "working directory, uncommitted" pseudo-option. Independent of
tickets 170/171 — this is pure git plumbing plus a route.

## Acceptance criteria

- A function (e.g. in a new `graphwerk/refs.py`, alongside the existing
  git-plumbing helpers in `differ.py`) that, given `repo_root`, returns a
  list of candidate refs: every local branch (`git for-each-ref
  refs/heads`), every tag (`refs/tags`), and the most recent N commits
  (`git log --oneline -n N` on the current branch; N is the implementer's
  call — 20 is a reasonable default), each with enough info to label and
  select it (ref name or sha, a short display label, and a `kind`:
  `branch`/`tag`/`commit`). Same permissive posture as the existing
  `_git_ls_tree`/`_git_show_bytes` helpers: a repo with no commits yet, or
  a `repo_root` that isn't a git repo at all, returns an empty list rather
  than raising.
- `GET /api/refs` in `graphwerk/server.py` returns this list plus one
  well-known entry representing "the working directory, uncommitted" using
  the sentinel token ticket 171 introduces (coordinate the token's exact
  string with whichever of 171/172 lands first).
- A test hits the route (or calls the underlying function directly) against
  a temp git repo with at least one branch, one tag, and a few commits, and
  asserts all three kinds appear with the expected fields, plus the
  working-directory entry.
- A test confirms the empty-list posture for a non-git directory.

## Likely files

- `graphwerk/refs.py` (new) — ref enumeration.
- `graphwerk/server.py` — the route.
- `tests/test_refs.py` (new) or `tests/test_server.py` — route/function tests.

## Out of scope

- Any pagination, search-by-message, or filtering beyond
  branches + tags + recent N commits (ADR 060's explicit deferral).
- Wiring the frontend dropdown to this endpoint — that's ticket 174.
