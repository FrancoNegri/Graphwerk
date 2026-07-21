# 157. Differ reads base content via a git ref, not a second directory

Status: done
Decision: docs/decisions/058-retire-worktree-single-directory-review.md

## Goal

`ChangeSetBuilder`/`GraphService` (`graphwerk/service.py`) compare the
developer's single working directory against a git ref (default: the
commit `HEAD` pointed at when the review session started) instead of
walking a second `staged_root` directory tree. "Staged" content is
whatever's currently on disk; "base" content is read via `git show
<ref>:<path>` (or equivalent plumbing). The symbol-diff logic itself
(parse both texts, compare by qualified name) is unchanged.

## Acceptance criteria

- `GraphService`/`ChangeSetBuilder` accept one working directory plus a
  base ref, not two directory paths.
- A file changed on disk relative to the base ref shows up in the diff
  exactly as it does today with two directories.
- A file identical to the base ref's content shows up as unchanged.
- A file present at the base ref but deleted on disk shows up as deleted;
  a file absent at the base ref but present on disk shows up as new.
- Reading base content for a path that doesn't exist at the given ref
  (new file) is handled without error.

## Likely files

- `graphwerk/service.py` — `GraphService`, `ChangeSetBuilder`: swap the
  second directory walk for git-ref reads. (`ChangeSetBuilder` itself
  actually lives in `graphwerk/staging/differ.py`, not `service.py` — this
  ticket's own "likely files" was slightly off; noted here rather than
  silently absorbed.)
- `graphwerk/bootstrap.py` — `GraphService`'s two callers (`server.py`'s
  `/api/graph` payload, `bootstrap.py`'s construction) needed a one-line
  compatibility patch to keep compiling/running under the new signature
  ahead of ticket 158's real CLI rewire. `bootstrap.py` passes `staged` as
  `repo_root` and the literal string `"HEAD"` as `base_ref` — correct for
  the current worktree/demo layout (the worktree's HEAD never advances past
  its own branch point), but a placeholder ticket 158 replaces.

## Out of scope

- Anything about where the CLI gets the working directory or ref from
  (ticket 158).
- Any change to the symbol-diff/qualified-name comparison logic itself.

## Known interim gap (accepted, not fixed here)

`CommitEngine`/`DiscardEngine` (`graphwerk/commit.py`, `graphwerk/discard.py`)
still construct their own `ChangeSetBuilder` the old two-directory way
(`ChangeSetBuilder(base, staged)`), which the new `(repo_root, base_ref)`
signature silently misinterprets as `repo_root=base, base_ref=str(staged)`
— an invalid ref that resolves to an empty base tree. `/api/commit` and
`/api/discard` are therefore unreliable (e.g. discard can delete a modified
file instead of reverting it) until ticket 159 deletes both engines. This
was surfaced and accepted deliberately rather than discovered later: six
tests in `tests/test_commit.py`, `tests/test_discard.py`, and
`tests/test_server.py` are marked `xfail` with a reason pointing here, so
the suite states the gap instead of hiding it. Ticket 159 resolves this by
deleting the affected code, not by fixing it in place.
