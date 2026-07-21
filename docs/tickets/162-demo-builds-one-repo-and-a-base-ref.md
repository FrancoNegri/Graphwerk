# 162. `graphwerk demo` builds one repo + a base ref, not two demo trees

Status: done
Decision: docs/decisions/058-retire-worktree-single-directory-review.md

## Goal

The scripted demo (`graphwerk demo`) matches the new single-directory
model: it builds one demo repository, commits an initial state, makes its
scripted edits on top, and serves that directory against the initial
commit as the base ref — instead of building separate base/staged demo
trees.

## Acceptance criteria

- `graphwerk demo` produces one directory on disk, not two.
- `graphwerk demo --no-serve` still resets the demo directory back to its
  scripted starting state for repeated runs.
- The served graph shows the same scripted modified/new/deleted node
  states as before, computed against the recorded initial commit.

## Likely files

- `graphwerk/demo.py` — `build_demo()`: one repo + initial commit instead
  of base/staged directory pair.
- `graphwerk/cli.py` — `demo` subcommand wiring to `_serve`.

## Out of scope

- Any change to what the scripted demo edits actually contain.
