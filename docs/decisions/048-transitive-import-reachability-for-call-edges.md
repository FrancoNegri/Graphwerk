# 048. Call-edge reachability follows re-export chains, not just direct imports

Status: proposed
Date: 2026-07-18

## Context

Phase 2's exit criterion (docs/04-roadmap.md) is literally "build a
graphwerk feature using graphwerk to review it" — dogfooding graphwerk's
own repo is in scope, the same category that produced ADR 032 and ADR 034
against the agendabot dogfood graph. This finding comes from that same
kind of look, turned on graphwerk itself: on the current graph,
`graphwerk/rationale/miner.py` shows **zero incoming `calls` edges**,
which reads as "nothing uses this file." It's wrong — `RationaleStore`
(defined in `miner.py`) is constructed in `graphwerk/cli.py::_serve`
(`graphwerk/cli.py:117`) and is the load-bearing class for the entire
rationale subsystem (docs/02's "per-node rationale").

Traced against `GraphService._add_call_edges` / `admitting_modules_by_file`
(`graphwerk/service.py:171-252`, the mechanism ADR 034 added): `cli.py`
imports `graphwerk.rationale` (not `graphwerk.rationale.miner`) —
`from graphwerk.rationale import RationaleStore`. `ModuleFileResolver`
correctly resolves `graphwerk.rationale` to `graphwerk/rationale/__init__.py`.
But `RationaleStore` isn't *defined* in `__init__.py` — that file only
contains `from graphwerk.rationale.miner import RationaleStore` (a
re-export), so the extractor (which only turns `ClassDef`/`FunctionDef`
into symbols) creates no `RationaleStore` symbol there at all. The one and
only symbol named `RationaleStore` lives in `miner.py`. ADR 034's
reachability check is one hop only: `allowed_files = {caller_rel,
*modules_by_file}`, where `modules_by_file` comes from resolving `rel`'s
*own* direct imports. `graphwerk/rationale/miner.py` is never in that set
for `cli.py` — only `graphwerk/rationale/__init__.py` is — so the real
`cli.py::_serve → miner.py::RationaleStore` call edge gets filtered out by
the same check ADR 034 added to kill phantom edges.

This is the mirror-image failure of ADR 034's own motivating bug: ADR 034
fixed an edge that was drawn but shouldn't exist (phantom, invented
relationship); this is an edge that should exist but isn't drawn
(dropped, real relationship). Both undermine the same thing docs/02 names
as the point of the graph: "does the stated intent match what the code
actually does" requires the graph's own claims — including "no callers" —
to be trustworthy. A package `__init__.py` re-exporting names from a
submodule is not an edge case; it's one of the most common Python
packaging idioms, and this repo's own `graphwerk/rationale/__init__.py`
uses it. Any package with this shape will show its implementation module
as falsely orphaned.

ADR 034's "Out of scope" section lists wildcard imports, dynamic calls,
relative-import dot-level (ticket 054, unrelated — that's about resolving
`from .x import y` to the right file, not about re-export chains), and
symbol-move detection. Re-export chains aren't among them — this is a real
gap, not a previously-deferred item resurfacing.

## Decision

Generalize `_add_call_edges`'s reachability check from "the caller's own
file, or a file it directly imports" (ADR 034) to "the caller's own file,
or any file transitively reachable by following resolved imports" —
matching actual Python name resolution, where `from pkg import Name` can
legally reach a symbol defined several packages deep through a chain of
re-exporting `__init__.py` files.

Concretely, in `graphwerk/service.py`:

- Add a memoized, cycle-guarded traversal that, starting from a caller's
  `rel_path`, follows `admitting_modules_by_file`'s existing one-hop
  resolution repeatedly (module → resolved file → that file's own
  imports → ...) to build the full reachable-file set, staying within the
  same tree (base or staged) the ADR 032 caller-status branch already
  selects at every hop — never crossing from a base-only file into a
  staged-only one or vice versa.
- Use that reachable-file set (instead of the one-hop `modules_by_file`
  keys) to build `allowed_files` in `_add_call_edges`.
- `via_imports_entries` currently indexes `modules_by_file[target_rel]`
  unconditionally once `target_rel != caller_rel`; since `target_rel` can
  now be reachable without being a *direct* one-hop import, guard that
  lookup and return `None` when the target isn't in the direct
  one-hop map — same "no explanation available" fallback the code path
  already uses for same-file calls. Producing an actual multi-hop
  explanation (which import statements chain together to admit the edge)
  is real, separable work — see Out of scope.

No change to `FileIndex`, `SymbolInfo`, or the extractors: this stays
entirely inside already-extracted `imports` data, reusing
`ModuleFileResolver` exactly as ADR 034 introduced it, just applied
repeatedly instead of once.

## Alternatives considered

- **Special-case "unused single-name import = re-export"** — detect that
  a file imports a name it never itself calls, and treat that as an alias
  hop. Rejected: needs a fragile heuristic to distinguish a genuine
  re-export from a merely-unused import or a `__all__`-listed symbol, and
  ultimately computes the same transitive-file information the general
  traversal already needs — more special-casing for no less code.
- **Do nothing / document as a known limitation** — zero cost, but leaves
  a confirmed, live false-negative on graphwerk's own dogfood graph (the
  exact scenario Phase 2 exists to catch), and specifically on the
  rationale subsystem docs/02 calls out as differentiating this tool from
  a diff viewer. Rejected on the same grounds ADR 034 rejected it for the
  phantom-edge case, just the opposite direction of error.

## Consequences

- Closes the false-negative class: a caller can now resolve to a symbol
  reached through any chain of resolvable imports, not just a direct one,
  while ADR 032/034's phantom-edge protections (tree membership, one-hop
  reachability) still apply at every hop of the chain.
- `_mark_affected` (blast radius) gains real edges it was silently
  missing — a change to `miner.py::RationaleStore` will now correctly
  mark `cli.py::_serve` as `affected`, restoring a blast-radius signal
  docs/02 names as core to the concept.
- `via_imports` becomes `None` (no explanation shown) for any edge whose
  only path is multi-hop, until the follow-up ticket below. This is a
  strictly better default than today's behavior (the edge doesn't exist
  at all), not a regression.
- Slightly more computation per snapshot (bounded traversal over an
  already-small resolved-file graph); no new dependency, no model change,
  consistent with every standing invariant.

## Out of scope

- Multi-hop `via_imports` provenance (showing the actual chain of import
  statements that admits a transitively-reached edge) — real UI-facing
  work, its own ticket below.
- Relative-import dot-level resolution — stays on ticket 054, unrelated.
- Wildcard imports, dynamic calls (`getattr`, decorators, metaclasses) —
  stays out of scope per ADR 034, undecidable in general.
- Symbol-move detection — stays deferred per ADR 032.
