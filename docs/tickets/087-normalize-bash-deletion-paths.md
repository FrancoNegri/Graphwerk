# 087. Normalize relative paths in Bash deletion tracking

Status: done
Decision: docs/audit/runs/001-2026-07-17.md

## Goal

A Bash deletion like `rm ./old.py` or `rm sub/../old.py` produces an
`EditEvent` whose `rel_path` matches the differ's node id (`old.py`), the
same way absolute paths already do via `_to_staged_rel`. Today relative
tokens are kept verbatim, so the deleted file never enters the set
`attribute_files` scans (nor the proximity fallback), silently
reintroducing the ADR 026 gap for common command shapes.

## Acceptance criteria

- `_bash_deleted_rel_paths("rm ./old.py", staged_root)` yields
  `["old.py"]`; same for `git rm` and for `a/../b.py`-style tokens
  (normalized without touching the filesystem — the file is deleted by the
  time the transcript is mined, so resolution must be lexical).
- A plain already-relative token (`rm src/x.py`) keeps today's behavior.
- Absolute-path handling is unchanged.
- A regression test in `tests/rationale/test_transcript.py` covers the
  `./`-prefixed case end-to-end (transcript line → EditEvent rel_path).

## Likely files

- `graphwerk/rationale/transcript.py` — normalize relative tokens
  (e.g. `PurePosixPath` lexical normalization) before emitting.
- `tests/rationale/test_transcript.py` — new cases.

## Out of scope

- Broad shell parsing (quoting, subshells, `mv`) — ADR 026 scoped
  deletion tracking to `rm`/`git rm` on purpose.
- Tracking the agent's working directory across `cd` — no observed case
  yet; lexical normalization covers the shapes seen.
