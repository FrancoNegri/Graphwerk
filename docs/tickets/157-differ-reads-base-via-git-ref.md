# 157. Differ reads base content via a git ref, not a second directory

Status: ready
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
  second directory walk for git-ref reads.

## Out of scope

- Anything about where the CLI gets the working directory or ref from
  (ticket 158).
- Any change to the symbol-diff/qualified-name comparison logic itself.
