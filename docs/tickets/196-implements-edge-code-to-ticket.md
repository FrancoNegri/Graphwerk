# 196. `graphwerk/history.py` + `implements` edges from files to their ticket

Status: ready
Decision: docs/decisions/065-decision-lineage-graph.md

## Goal

Every file a landed ticket's commit(s) actually touched gets a real
`implements` edge into that ticket node — ground truth mined from git
history, replacing any need to trust a ticket's "Likely files" prose.

## Acceptance criteria

- New `graphwerk/history.py`:
  - `commits_for_ticket(repo_root: Path, ticket_number: int) -> list[str]`
    — shells out to `git log --all --format=%H --grep='^Ticket {n}:'`
    (mirrors the existing subprocess pattern in `graphwerk/staging.py`/
    `graphwerk/landing.py` — no new dependency).
  - `changed_files_for_commits(repo_root: Path, shas: list[str]) ->
    set[str]` — `git diff-tree --no-commit-id --name-only -r <sha>` per
    commit, unioned, paths normalized repo-root-relative.
- `GraphService.snapshot()` (or a clearly separated helper it calls), for
  every ticket node in the doc domain, resolves its ticket number from its
  filename (`docs/tickets/NNN-....md`), looks up its commits, and emits
  `GraphEdge(source=<file node id>, target=<ticket id>, kind=
  "implements")` for every file returned — file-granularity only, per ADR
  065's explicit scope line.
- A ticket number with no matching commits (not yet landed, or a
  numbering gap) produces no edges, not an error.
- Only files that still exist as nodes in the current snapshot get edges
  (a file later deleted or renamed doesn't produce a dangling edge) — same
  defensive posture as ticket 192.
- A test against a small throwaway git repo fixture (a few commits with
  `Ticket NNN:`-prefixed messages touching known files) asserts the right
  edges appear.

## Likely files

- `graphwerk/history.py` (new).
- `graphwerk/service.py` — wiring step.
- `tests/` — new test module for `history.py`, plus a snapshot-level test.

## Out of scope

- Symbol-level attribution (which qualnames within each file changed) —
  file-level only, per ADR 065.
- Any UI-facing decision about how this cross-domain edge renders when
  the Design/Implementation toggle (ADR 046) hides one side — ticket 197.
- Performance/caching of repeated `git log --grep` calls across many
  tickets — acceptable to call once per ticket per snapshot build for now;
  revisit only if dogfooding shows it's slow (same posture as ADR 019's
  original perf deferral).
