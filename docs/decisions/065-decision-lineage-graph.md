# 065. Decision lineage graph: root pitch → typed ADR relationships → tickets → code

Status: proposed
Date: 2026-07-22

## Context

Graphwerk's own process — this very skill — is exactly the thing docs/02
argues a flat diff can't show: structural context, blast radius, and *why*,
for a decision instead of a code change. Every ADR here already names the
ADRs it builds on, narrows, or replaces in prose ("Supersedes ADR 037",
"Narrowly amends ADR 058", "extends the ADR 005 split"); every ticket
already names its ADR (`Decision: docs/decisions/NNN-....md`); every
`git log` entry already names its ticket (`Ticket 185: synthesize the
Root...`). None of it is rendered as a graph today — ADR 046 got the doc
domain indexed and cross-linked, but only as one undifferentiated
`references` edge kind, with no distinguished root and no bridge back to
the code it produced. The user's ask: make graphwerk show its own
lineage — pitch → decision → decision-that-narrows-it → ticket → the actual
diff — as one explorable graph, the same way it already shows a codebase's
structure.

This is a continuation of ADR 046's detour (knowledge-base-graph), not a
new one — that ADR already chose to generalize the existing graph
machinery to the doc domain rather than build a second product surface;
this decision extends that same graph with typed edges and one more hop
(doc → code) rather than reopening the question of whether to have a doc
domain at all. Phase 2's roadmap stays exactly as deferred as ADR 046
already left it.

ADR 063 (`Root` node) explicitly flagged the doc-domain equivalent as out
of scope, pending "doc-file layering... consum[ing] `references` edges" —
this decision doesn't need that prerequisite, because unlike the code
domain (many equally-valid entry-point files, hence a synthetic anchor),
the doc domain already has one specific, real, always-indexed file that
*is* the root by name: `docs/02-product-concept.md`. No synthetic node
needed here at all.

## Decision

Four additive pieces, all reusing the existing `FileIndex`/`GraphEdge`
contract — no new model classes, no new domain:

**1. Typed ADR-to-ADR relationships, parsed the same deterministic way
`Decision:` lines already are.** A new three-line convention directly
under an ADR's `Status:`/`Date:` header, comma-separated ADR numbers:

```
Supersedes: 037, 050
Amends: 058
Extends: 005
```

`graphwerk/indexing/markdown.py` (ADR 046's extractor) parses these into
`FileIndex.adr_relationships: dict[str, set[str]]` (kind → target rel
paths, resolved via the same `docs/decisions/NNN-*.md` globbing the
`north-star`/`ticket` skills already do to find "the next number").
`GraphService` wires each into its own `GraphEdge.kind`
(`"supersedes"` / `"amends"` / `"extends"`), source = this ADR, target =
the named one. Three kinds, chosen because they're the only distinctions
this repo's own ADR prose already draws consistently:

- **supersedes** — the old decision's mechanism is fully replaced (058
  supersedes 037 and 050). Subsumes what a few ADRs call "retires" — a
  retirement is just a supersession with no replacement decision named;
  that nuance is visible in the target ADR's own `Status` field
  (`retired`, ADR 058 style) without needing a fourth edge kind.
- **amends** — a *separate* ADR narrows or scopes an exception into a
  still-standing decision without replacing it (061 amends 058: "the
  whole-tree exception," not a reversal).
- **extends** — purely additive: builds on a decision that keeps meaning
  exactly what it did before (041 extends 005's split).

(In-place revision notes inside one ADR's own file — the existing
`*Amended <date>: ...*` convention seen in ADRs 029/033/041/054/etc. — stay
exactly as they are: that's one document's own history, not a relationship
between two nodes, so it's out of scope here; see Out of scope.)

**2. `docs/02-product-concept.md` as the graph's literal root, via one new
edge kind, `grounds`.** After ADR relationship edges are wired, any ADR
node with no incoming `supersedes`/`amends`/`extends` edge (i.e., not
itself a follow-on to another ADR) gets `GraphEdge(source="docs/02-
product-concept.md", target=<that ADR>, kind="grounds")`. Computed in
`GraphService.snapshot()` as a post-processing step over already-built
edges — the same category of work `_mark_affected`/`Root` (ADR 063)
already are, just pointed at a real node instead of a synthetic one.

**3. `implements`, ticket → ADR — promoted out of the generic
`references` bucket.** The `Decision: docs/decisions/NNN-....md` line
`markdown.py` already parses (ADR 046/052) is completely unambiguous:
every ticket names exactly one ADR. Give it its own edge kind instead of
folding it into catch-all `references`, so the UI can draw "the decision
this ticket implements" distinctly from an arbitrary inline mention.
Direction: ticket → ADR (mirrors `calls`/`uses`: edge points from the
thing that depends on a decision to the decision itself).

**4. `implements`, code → ticket — mined from real git history, not
"Likely files" prose.** Every landed ticket's commit already starts
`Ticket NNN: ...` (this repo's own convention, visible in `git log`
today). A new small module, `graphwerk/history.py`:
   - `commits_for_ticket(repo_root, ticket_number) -> list[str]` — `git
     log --all --grep='^Ticket {n}:'`.
   - `changed_files_for_commits(repo_root, commits) -> set[str]` — `git
     diff-tree --no-commit-id --name-only -r <sha>` against each, unioned.

  `GraphService` emits `GraphEdge(source=<file node id>, target=<ticket's
  rel path>, kind="implements")` for each such file — **file granularity
  only** for this pass (see Alternatives/Out of scope for why not
  symbol-level). This is the one piece that's genuinely cross-domain (a
  `code`-domain file node pointing at a `doc`-domain ticket node); ADR
  046's "Design"/"Implementation" mode toggle filters *nodes*, not edges,
  so the ticket implementing this decides how these render when the
  opposite domain is hidden (e.g., always-visible regardless of toggle,
  since they're the one edge kind that's *supposed* to cross the
  boundary) — a display detail, not an architectural one.

Net result: click `docs/02-product-concept.md` → see every foundational
ADR; click an ADR → see what it supersedes/amends/extends and which
tickets implement it; click a ticket → see exactly which files its actual
landed commit touched. One connected graph, pitch to diff.

## Alternatives considered

- **Infer relationship types (and code linkage) from prose/semantics via
  an LLM pass** — would catch relationships the deterministic line-based
  convention misses (a lot of "ADR NNN" mentions in this very corpus are
  casual references, not formal relationships). Rejected for the same
  reason ADR 046 already rejected it: "the differ's whole model is
  'compare by qualified name... no fuzzy mapping'" — nondeterministic
  inference doesn't belong in a review surface that's supposed to be
  ground truth, and it would need to re-run (and could re-answer
  differently) every time the graph refreshes.
- **Mine "ADR NNN" mentions in prose directly, no new convention** —
  free, no backfill work, but as this repo's own corpus shows, a bare
  number in prose doesn't disambiguate "this ADR supersedes 037" from "as
  discussed in ADR 037" — exactly the false-positive problem that would
  make the graph actively misleading, the same class of failure ADR 052
  fixed for admitting imports. Rejected in favor of the explicit-line
  convention, same posture as `Decision:`/ticket 126's inline-link
  parsing.
- **A synthetic `__root__`-style doc node (ADR 063's pattern), instead of
  pointing straight at `docs/02-product-concept.md`** — consistent with
  the code domain's Root, but the doc domain already has one specific,
  named, always-present real node that *is* the founding document; adding
  a synthetic stand-in for something real that already exists just adds a
  node the user would need to learn is "the same as docs/02, sort of."
  Rejected — simpler to point at the real thing.
- **Symbol-level ticket → code edges (mine the ticket's commit diff down
  to changed qualnames, not just files)** — more precise, and the differ
  already supports diffing arbitrary revision pairs (ADR 060) so the
  machinery exists. Deferred, not rejected outright: a ticket's commit
  routinely touches 3-8 files with a handful of symbols each; at
  file-level that's already a manageable fan-out for the graph, while
  symbol-level would roughly multiply edge count by the average symbols-
  per-file and needs the ticket-to-commit-range logic to also carry
  qualname resolution across a range that might span several commits.
  Start at file granularity (matches ADR 051's own precedent of adding
  granularity incrementally); revisit if file-level proves too coarse in
  practice.
- **Derive ticket → code from the ticket's own "Likely files" section
  instead of git history** — no git-log mining needed, cheaper. Rejected:
  "likely" is a plan written *before* implementation, and this repo's own
  history shows it drifts (tickets get scoped down, files change during
  TDD). A commit that says "Ticket NNN" is ground truth for what actually
  landed; "Likely files" stays exactly what it already is today — planning
  prose, not a link source.

## Consequences

- Three new `GraphEdge` kinds (`supersedes`, `amends`, `extends`) plus two
  more (`grounds`, and `implements` used at both the ticket→ADR and
  code→ticket hops) — no new node kind, no new model class; `GraphEdge`
  already carries an arbitrary string `kind`.
- `FileIndex` gains one field (`adr_relationships`) — additive, degrades
  to empty for every non-ADR Markdown file and for any future non-Python,
  non-Markdown extractor.
- Existing ADRs need a one-time backfill (a docs-only ticket) adding the
  new relationship lines where their own prose already unambiguously
  states one — `Supersedes`/`Amends`/`Extends` don't retroactively invent
  anything the ADR didn't already claim in words.
- `implements` now means two different hops (ticket→ADR, code→ticket) —
  deliberately, so "traces up to the decision that caused this" reads as
  one consistent arrow style across all three hops (code → ticket → ADR →
  root), rather than inventing a fourth vocabulary word for what is, from
  the reviewer's point of view, the same kind of question asked twice.
- `graphwerk/history.py` is the first module that reads git *history*
  (not just two ref snapshots) — a new but small capability, reusing the
  same `git` subprocess pattern `GitRefRevision`/`landing.py` already
  established; no new dependency.
- No invariant touched: no hunk-to-symbol mapping (file-granularity
  `git diff-tree --name-only`, not a hunk mapper); `FileIndex`/`SymbolInfo`
  stay language-neutral; Python-side computation throughout, JS stays a
  payload consumer; no new backend dependency.

## Out of scope

- Backfilling *in-place* `*Amended <date>: ...*` notes into the new
  cross-ADR convention — those are one document's own revision history,
  not an edge between two nodes; left exactly as they are.
- Symbol-level (rather than file-level) code → ticket edges — see
  Alternatives; revisit once file-level is dogfooded.
- A fourth "retires" edge kind distinct from `supersedes` — the
  replaced-vs-removed distinction lives in the target ADR's own `Status`
  field, not a separate edge kind, for this pass.
- Any change to the existing generic `references` edge kind or ADR 046's
  inline-link/`Decision:`-line parsing mechanics beyond promoting the
  `Decision:` line specifically to `implements` — arbitrary prose links
  keep rendering as `references`, unchanged.
- Enforcing/linting that new ADRs *use* the relationship convention — same
  advisory posture as ADR 012/047's session guidance; nothing breaks if an
  ADR omits it, it just gains no typed edges.
- A "commits since last ticket-touching-this-file" reverse view (code node
  → *all* tickets that ever touched it, historically) — this decision
  wires the ticket that most recently/currently claims a file, not a full
  historical audit trail; a repo where two tickets touch the same file
  over time gets two `implements` edges into that file, which is fine and
  requires no extra design, but a dedicated "history" browsing UI is not
  part of this decision.
- Any change to the `Design`/`Implementation` mode toggle's own filtering
  logic beyond deciding how the new cross-domain edge renders — ADR 046
  stands as-is otherwise.
