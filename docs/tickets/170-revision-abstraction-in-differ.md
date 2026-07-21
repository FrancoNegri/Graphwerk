# 170. `Revision` abstraction in the differ

Status: done
Decision: docs/decisions/060-comparison-picker-any-ref-vs-any-ref.md

## Goal

`ChangeSetBuilder` currently hard-codes one side of the comparison to a git
ref (`base_ref: str`, read via `git show`/`git ls-tree`) and the other side
to always be the live working directory (read from disk). This ticket
extracts both into a common `Revision` interface with two implementations,
so a later ticket can put either kind of revision on either side, with no
behavior change yet — this ticket is a pure refactor.

## Acceptance criteria

- A `Revision` interface (or equivalent minimal protocol) in
  `graphwerk/staging/differ.py` with two implementations:
  - `GitRefRevision(repo_root, ref)` — wraps today's `_git_ls_tree` /
    `_git_show_bytes` logic (path listing + blob bytes at a ref).
  - `WorkingTreeRevision(repo_root)` — wraps today's `_index_tree` /
    `_read_bytes` disk-reading logic.
- `ChangeSetBuilder.__init__` takes `base: Revision, staged: Revision`
  instead of `base_ref: str` (staged's revision is implicitly "the working
  directory" today, now explicit).
- All existing caching behavior is preserved: base-side reads stay cached
  per revision instance (a commit's content never changes for the
  builder's lifetime); working-tree reads stay keyed by
  `(rel_path, mtime_ns, size)` as today.
- `tests/staging/test_differ.py` passes unmodified in intent (constructor
  call sites updated to pass `GitRefRevision(...)` / `WorkingTreeRevision()`
  instead of a bare ref string) and covers at least one case of each
  `Revision` implementation directly (path listing + bytes-at-a-path).
- No behavior change: `ChangeSetBuilder(repo_root, GitRefRevision(repo_root, ref), WorkingTreeRevision(repo_root)).build()` produces identical `FileChange` output to today's `ChangeSetBuilder(repo_root, ref).build()`.

## Likely files

- `graphwerk/staging/differ.py` — the refactor.
- `tests/staging/test_differ.py` — updated construction, new `Revision`-level tests.

## Out of scope

- Anything above `ChangeSetBuilder` (`GraphService`, `server.py`,
  `bootstrap.py`) — those callers are updated in ticket 171. This ticket
  only needs `ChangeSetBuilder`'s own constructor and internals to change;
  update its direct callers no further than making the code compile if
  strictly necessary, but the real caller rewiring is 171's job.
- Putting a `GitRefRevision` on the "staged" side or vice versa in any
  running code path — that's what tickets 171-172 wire up; this ticket
  just makes it *possible*.
