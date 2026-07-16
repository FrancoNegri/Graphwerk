# 055. Cache parsed `FileIndex` per file by mtime/size fingerprint

Status: done
Decision: docs/decisions/019-snapshot-recompute-caching.md

## Goal

`ChangeSetBuilder.build()` no longer re-parses a file's AST (and re-walks it
for call names) on every call if that file hasn't changed since the last
call — cost becomes proportional to files actually touched, not repo size.

## Acceptance criteria

- Calling `ChangeSetBuilder.build()` twice in a row with no filesystem
  changes between calls does not invoke `PythonAstExtractor.extract` again
  for any file the second time (test via a call-count spy on the
  extractor).
- Touching one file (changing its mtime and/or size) between two `build()`
  calls causes only that file to be re-parsed on the next call; all others
  are served from cache.
- Cache is keyed by `(root, rel_path, mtime_ns, size)` — the same
  fingerprint shape `GraphService.state_hash()` already uses — so it can't
  silently serve stale data after an edit.
- Existing differ/service tests (symbol status, call edges, diffs) pass
  unchanged.

## Likely files

- `graphwerk/staging/differ.py` — `ChangeSetBuilder` gains an instance-level
  cache and stops calling the uncached `index_tree(root)` fresh on every
  `build()`.
- `graphwerk/indexing/python_ast.py` — may need a small helper to fingerprint
  a file (stat-based), reused from/consistent with `service.state_hash()`.

## Out of scope

- Caching at the `GraphService`/API layer (that's ticket 056, code view).
- Cache eviction or memory bounds — unbounded growth over one process
  lifetime is accepted for now (see ADR 019, out of scope).
