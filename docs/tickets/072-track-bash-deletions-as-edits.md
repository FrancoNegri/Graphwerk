# 072. Track Bash-performed file deletions as transcript edit events

Status: ready
Decision: docs/decisions/026-rationale-for-deleted-files.md

## Goal

A file removed via a `Bash` tool call (`git rm <path>`, `rm <path>`)
should become eligible for mention-based attribution and the proximity
fallback, the same as a file touched by `Edit`/`Write` — so a deletion
narrated only in prose, with no dedicated bullet at all, can still be
attributed.

## Acceptance criteria

- `parse_transcript` recognizes `git rm <path...>` and `rm <path...>`
  inside `Bash` tool-call commands and emits an edit-shaped event (reusing
  `EditEvent`'s `last_segment_index` anchoring) for each path removed.
- The deleted path is included in the `rel_paths` set passed to
  `attribute_files`, and gets the same proximity-fallback treatment as
  Edit/Write-touched files.
- Reproduces: given a transcript whose only mention of a deletion is
  prose (no guidance bullet at all — simulate by using a segment that
  names the file without the bullet shape), `attribute_files` still finds
  and attributes it.

## Likely files

- `graphwerk/rationale/transcript.py` — recognize `git rm`/`rm` commands
  in `Bash` tool_use blocks.
- `graphwerk/rationale/miner.py` — confirm `rel_paths` derivation picks up
  the new event kind unchanged.
- `tests/rationale/test_transcript.py`.

## Out of scope

- Renames/moves (`git mv`, `mv old new`).
- Broader shell-command parsing beyond `git rm`/`rm`.
