# 004. Show source for any selected node, not just diffs

Status: proposed
Date: 2026-07-14

## Context

Today the sidebar only fills in when a node changed: `diff-section` renders
`node.diff`, which is only populated for modified/added/deleted symbols and
files (`graphwerk/service.py`, `change.symbols`/`change.diff`). Click an
unchanged file, class, or function — the common case, since ticket 010 made
unchanged files collapse by default and most of a codebase is unchanged at
any given time — and the sidebar shows only the status chip and path, no
code. The underlying text is already sitting in `SymbolInfo.source`
(`graphwerk/models.py`) and on disk for files; it's just never threaded
through to the node payload.

Docs/02's core claim is that the graph is a *better review surface than a
diff* because it carries structural context. That claim is weaker than it
could be if the graph can only show you code that changed — a reviewer
following a call edge to understand *why* a change is safe currently hits a
dead end at the first unchanged node. This isn't gated on any roadmap phase
(no session control, no apply-semantics work needed) — it's a direct,
low-risk widening of the existing v1 review surface, so there's no reason to
defer it to a later phase.

## Decision

Thread full source text through to every node, file and symbol alike, and
show it in the sidebar as the fallback view whenever there's no diff:

- **Symbol nodes:** `graphwerk/service.py` already resolves `info`
  (`SymbolInfo`) per symbol to build the diff; also assign `info.source` to
  a new `GraphNode.source` field. Free — the value already exists at that
  point in the loop.
- **File nodes:** capture the file's full text while `FileChange` is built
  (`graphwerk/staging/differ.py`) — staged content, or base content if the
  staged side is missing (deleted file) — and carry it on `FileChange` so
  `service.py` can assign it to `GraphNode.source`.
- **Frontend:** `showDetails()` keeps the existing diff section untouched
  for changed nodes; add a new code section that renders `node.source`
  verbatim whenever `node.diff` is empty, so unchanged nodes get a read-only
  code view instead of a blank panel.

## Alternatives considered

- **Lazy per-node endpoint** (e.g. `GET /api/source/<id>`, fetched on
  click) — keeps `/api/graph` payload smaller, but adds a new endpoint and
  a round-trip, and departs from the precedent ADR 001 already set
  explicitly ("server-side graph filtering... pushes view state into the
  API... rejected, the snapshot is already small enough to ship whole").
  Rejected for the same reason; revisit only if a real dogfood run (the
  project's established bar — see ADR 001/002 Flask numbers) shows the
  payload is actually a problem.
- **Show source and diff together for changed nodes** — more complete but
  wasn't asked for and doubles panel content for the common review case;
  rejected. Diff stays the primary view when one exists; source only fills
  the gap when there isn't one.

## Consequences

- `/api/graph` payload grows — every node now carries its full text, not
  only changed ones. Acceptable at the scale this project has actually
  measured (Flask, 959 nodes, ~1s/snapshot per ADR 001's validation); watch
  it on the next real-repo dogfood run rather than pre-optimizing.
- The graph becomes usable to *read* the codebase in its structural context,
  not only to review what changed — a real widening of docs/02's promise.
- No invariant touched: `FileIndex`/`SymbolInfo` already carried this data,
  this just threads it one hop further through the existing differ →
  service → snapshot pipeline. No new backend dependency.

## Out of scope

- Syntax highlighting, line numbers in the code view.
- Lazy loading / pagination for very large files.
- Showing source differently for methods nested in a collapsed class —
  same fallback rule applies uniformly.
