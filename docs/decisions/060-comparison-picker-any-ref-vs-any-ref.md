# 060. Comparison picker: any ref against any ref, including uncommitted

Status: proposed
Date: 2026-07-21

## Context

ADR 058 already turned "base" into a git ref instead of a second directory:
the differ reads base content via `git show <ref>:<path>` and compares it
against whatever's on disk. But that ref is fixed once at server startup
(`--base-ref`, defaulting to `HEAD`), and the other side of the comparison
is hard-coded to be the live working directory — there's no way to ask
"what changed between these two commits" without restarting the server
with a new `--base-ref` and losing the working-directory view entirely.

This surfaced directly from dogfooding: reviewing agendabot against a
specific historical commit (`ed0a0776`) while wanting to also flip back to
"what's uncommitted right now" without relaunching. That's still docs/02's
core pitch — the graph as a structural review surface — just applied to a
second axis: not only "review the live agent's delta," but "review any two
points in this repo's history against each other," with the working
directory as one more option on that same axis rather than a special case.
This isn't listed on any current roadmap phase bullet; it's closest in
spirit to Phase 2's "real-repo hardening" (features that fell out of
actually using graphwerk against a real repo) rather than a detour, so it's
being scoped here rather than deferred.

## Decision

1. **Generalize the differ's two sides behind a small `Revision`
   abstraction** (`graphwerk/staging/differ.py`): `GitRefRevision(ref)`
   (today's base-reading logic — `git ls-tree` / `git show`) and
   `WorkingTreeRevision()` (today's staged-reading logic — read from disk).
   `ChangeSetBuilder` takes `base: Revision, staged: Revision` instead of
   a fixed `base_ref: str` plus an assumption that "staged" means disk.
   The symbol-diff logic itself (parse both texts, compare by qualified
   name) doesn't change — only where the two texts can come from.

2. **`GET /api/refs`** enumerates branches, tags, and the most recent N
   commits on the current branch (via `git for-each-ref` / `git log
   --oneline -n N`), plus one well-known pseudo-ref meaning "the working
   directory, uncommitted" — the only option that can ever appear on
   either side today, now just one choice among several.

3. **`/api/graph` and `/api/hash` accept optional `base` / `staged` query
   params** (git ref strings, or the working-directory pseudo-ref).
   Omitting both preserves today's behavior exactly (the CLI's configured
   `--base-ref` vs. the working directory). The server keeps a small
   in-memory cache of `GraphService` instances keyed by `(base, staged)`,
   built the first time a pair is requested — the existing per-builder
   caches (index cache, code-view cache) then make repeat visits to a pair
   free, which matters because flipping back and forth between two refs is
   the expected usage pattern.

4. **Frontend: a base-ref / compare-to pair of dropdowns** in the header,
   sourced from `/api/refs`, defaulting to today's pair. Changing either
   refetches `/api/graph` with the new params and updates the existing
   "reviewing X against Y" line (ticket 165).

5. **Read-only history mode when `staged` isn't the working directory.**
   A live Claude session edits real files on disk — it has nothing to act
   on when both sides are frozen commits. When `staged` resolves to
   anything but the working directory: no rationale mining (that pair's
   `GraphService` gets a no-op `RationaleStore` — mining the live session's
   transcript against an unrelated historical diff would misattribute
   narration, not just omit it), the prompt box hides, and the frontend
   stops polling `/api/hash` (nothing about a frozen pair can change).
   Session control (`/api/prompt`, `/api/session`) stays tied to the one
   live `SessionCycle` regardless of which pair is being *viewed* — a
   session keeps running and keeps editing the working directory even
   while the developer is looking at an unrelated historical diff; it only
   can't be driven from that view.

## Alternatives considered

- **Only make `base` selectable, keep `staged` pinned to the working
  directory** — smaller change, and covers the most common "diff my
  in-progress work against an older point" case, but doesn't answer what
  was actually asked ("any commit against any commit, including
  uncommitted") and stops short of real history browsing.
- **A separate mode/subcommand for history browsing instead of query
  params on the running server** — avoids threading `base`/`staged`
  through `/api/graph`, but forces a relaunch to switch what's being
  compared, which defeats the point of a live dropdown.
- **Mutate the one running `GraphService`'s ref in place instead of
  caching an instance per pair** — less memory, but throws away the
  index/code-view caches on every dropdown change, making the common
  back-and-forth between two refs slow every time. Rejected in favor of
  the per-pair cache, which matches this codebase's existing precedent
  (ADR 019: unbounded, lifetime-scoped caches for "the pair being
  reviewed").

## Consequences

- `ChangeSetBuilder`'s constructor signature changes (`base_ref: str` →
  `base: Revision, staged: Revision`); every caller (`GraphService`,
  tests) updates accordingly.
- Memory grows with the number of distinct `(base, staged)` pairs visited
  in one server lifetime — unbounded, same posture as the existing
  `_index_cache`/`_code_view_cache` (ADR 019); not solved here, and not
  worse than what already exists for a single pair.
- Rationale stays accurate by only ever attaching to the one true live
  pair (the CLI's configured base vs. the working directory); every other
  pair simply shows no "why" rather than a misleading one.
- No invariant conflict: this only changes where the differ's two texts
  come from (still exactly two parsed trees, compared by qualified name,
  per docs/03/CLAUDE.md), adds no backend dependency, and the new UI
  control is plain JS in `static/`.

## Out of scope

- CLI flags to preset a non-default initial pair beyond today's
  `--base-ref` — the dropdown covers runtime switching; `--base-ref`
  keeps meaning "what to start with."
- Any git-mutating operation triggered from the UI (merge, rebase,
  checkout) — this is a view-only picker.
- Eviction/memory bounds on the per-pair `GraphService` cache (same
  deferral as ADR 019).
- A full commit browser: pagination, search-by-message, filtering beyond
  branches + tags + recent N commits. If "recent N" proves too shallow in
  practice, revisit as its own ticket rather than building search now.
