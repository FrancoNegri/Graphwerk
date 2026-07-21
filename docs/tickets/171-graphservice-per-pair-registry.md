# 171. `GraphService` per-`(base, staged)`-pair registry

Status: done
Decision: docs/decisions/060-comparison-picker-any-ref-vs-any-ref.md

## Goal

Depends on ticket 170. Introduce a small registry that builds and caches a
`GraphService` per `(base, staged)` ref pair, so the server can serve any
requested pair without restarting, while keeping today's single-pair
behavior as the zero-argument default. Non-live pairs (where `staged`
isn't the working directory) get a no-op rationale store, per ADR 060 —
mining the live session's transcript against an unrelated historical diff
would misattribute narration.

## Acceptance criteria

- A `ComparisonRegistry` (or equivalent) that, given `repo_root` and a
  default `(base_ref, staged_token)` pair, exposes `get(base, staged) ->
  GraphService`, constructing and caching a new `GraphService` (with its
  own `ChangeSetBuilder(repo_root, GitRefRevision(...)/WorkingTreeRevision(),
  ...)`, per ticket 170) the first time a given pair is requested, reusing
  it on repeat requests. Cache is unbounded for the process lifetime — same
  posture as `ADR 019`'s existing caches; no eviction logic needed.
- A well-known sentinel value (e.g. the literal string used as the
  "working directory" token) is recognized on either side of the pair and
  resolves to a `WorkingTreeRevision`; any other string is treated as a git
  ref and resolves to a `GitRefRevision`.
- When the resolved `staged` side is **not** the working directory, the
  `GraphService` built for that pair is constructed with a no-op
  `RationaleStore` equivalent (or `rationale=None` handled by `snapshot()`
  to skip mining/why entirely) rather than the real transcript-mining one.
- A test constructs the registry against a small git-initialized temp repo
  with at least two commits, requests two different `(base, staged)`
  pairs, and asserts: (a) both return usable `GraphService.snapshot()`
  results reflecting the correct diff for each pair, (b) requesting the
  same pair twice returns the same cached instance (identity check), (c)
  a pair where `staged` isn't the working directory yields nodes with no
  `why` set even when a real rationale source exists for the live pair.

## Likely files

- `graphwerk/service.py` or a new small module (e.g.
  `graphwerk/comparisons.py`) — the registry.
- `tests/test_service.py` (or a new `tests/test_comparisons.py`) — registry tests.

## Out of scope

- The `/api/refs` and `/api/graph`/`/api/hash` query-param wiring — that's
  tickets 172 and 173. This ticket only needs the registry to exist and be
  unit-testable on its own.
- Any frontend change.
