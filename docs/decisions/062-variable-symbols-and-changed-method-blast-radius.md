# 062. Global and class-variable symbols, wired as blast radius for changed methods

Status: proposed
Date: 2026-07-22

## Context

ADR 051/053 made "changed methods" the default code-view mode: selecting a
file or class narrows straight to just the leaf methods that changed,
because dogfooding showed the two older modes (`full`, `changes-only`)
either buried the change in unrelated code or stripped out the context
needed to read it. That mode solved "where's the diff" but not "what else
does this diff touch" — and docs/02's own framing of what makes this more
than a diff viewer is explicit: *"Blast radius for humans: color
affected-but-unchanged nodes... so the reviewer sees impact, not just
edits."* Today that blast-radius coloring only exists for one relationship
— function/method A calls changed function/method B (`_mark_affected` in
`graphwerk/service.py`) — because that's the only edge kind the graph
models. A method that mutates or reads a module-level global, or a
class-level attribute shared with sibling methods, leaves no trace on the
graph at all: those names aren't extracted as symbols, so there's no node
to color and no edge to draw. A reviewer staring at "changed methods" mode
has no way to see "this method's change also affects code that reads
`_CACHE`" without already knowing the codebase.

Separately: the enclosing class of a changed method already turns
`modified` today, for a reason worth making explicit rather than
rediscovering per-reader — `PythonAstExtractor._symbol` builds a class's
`SymbolInfo.source` from the class's full line span (`node.lineno` to
`node.end_lineno`), which includes every method's text. `ChangeSetBuilder`
diffs symbols by comparing `.source` text per qualname
(`graphwerk/staging/differ.py`), so a changed method's text changing means
the class's own text changes too, and the class node status flips to
`modified` automatically. This already serves the "indicate the class"
half of the request at the model layer; what's missing is surfacing it
*in the changed-methods panel itself*, where a reviewer is currently only
shown the method's own diff with no explicit line back to its class or to
any shared state it touches.

This is dogfooding-driven graph-legibility work in the same vein as ADR
022, 010, and 051/053 — none of those were literal Phase 2 roadmap
bullets either, but all shipped mid-phase because Phase 2's goal (docs/04)
is dogfooding until the review surface is actually usable, and each was a
concrete gap that surfaced from using the tool. This is the same kind of
gap, not a detour.

## Decision

Model module-level globals and class-level attributes as `SymbolInfo`
entries with a new `kind="variable"`, extracted by
`PythonAstExtractor` alongside classes/functions/methods:

- **Module-level**: simple `Name` targets of a top-level `Assign` /
  `AnnAssign` / `AugAssign` statement (not inside any function or class)
  become `qualname=<name>` variable symbols, parented to the file — same
  convention top-level functions already use.
- **Class-level**: simple `Name` targets of an `Assign` / `AnnAssign`
  directly in a class body (not inside a method) become
  `qualname="ClassName.<name>"` variable symbols — this already parents to
  the class node for free, since `GraphService.snapshot()`'s existing
  per-symbol loop derives `parent` from splitting the qualname on `.`
  exactly the way it already does for methods (`graphwerk/service.py:135`).
- Complex assignment targets (attribute, subscript, tuple/list unpacking)
  are skipped — only simple names are tracked. Instance attributes
  (`self.x = ...` inside a method body) are **not** treated as class-level
  variables; see Out of scope.

Because `SymbolInfo` is already a generic "named unit of code, diffed by
qualname" contract, and `ChangeSetBuilder`/`GraphService.snapshot()`'s
node-emission loop is already kind-agnostic (`kind=info.kind` flows
straight through), **no changes to the differ or to node emission are
needed** — a `variable` symbol gets a real status (`unchanged` /
`modified` / `added` / `deleted`), a real diff, and a real graph node the
same way a function does, for free.

What genuinely is new work:

1. **`SymbolInfo.uses: set[str]`** (`graphwerk/models.py`) — a field
   parallel to `calls`, populated by the extractor: for each
   function/method, the set of simple names it references (`ast.Name`,
   any context) that match a module-level global defined in the same
   file, plus `self.<attr>` attribute accesses that match a class-level
   variable defined on its own enclosing class. Kept separate from
   `calls` rather than folded into it — see Alternatives.
2. **A new `"uses"` edge kind**, wired in `GraphService` the same way
   `"calls"` edges are: `_add_call_edges` already builds `name_to_ids`
   (simple name → symbol node ids, variables included automatically since
   they're just another entry in `change.symbols`) and resolves targets
   through the existing shared-tree/import-reachability rules (ADR
   032/034/048). Generalize it to run once per `(attribute, edge_kind)`
   pair — `(calls, "calls")` and `(uses, "uses")` — reusing the exact same
   resolution logic rather than duplicating it.
3. **Generalize `_mark_affected` and `_mark_edge_status`** from
   `edge.kind == "calls"` to `edge.kind in {"calls", "uses"}`, so a
   variable read/written by a changed method turns `affected` (or its own
   real status, if it also changed) exactly the way an unchanged caller of
   a changed function already does — this is the actual blast-radius
   payoff.
4. **Frontend**: a `variable`-kind node style (small chip nested in its
   file/class compound, like methods already render — no new layer/order
   needed, same as methods today) and a `uses`-kind edge style, gated
   behind its own default-hidden toggle (ADR 013's existing pattern —
   edges start hidden, one checkbox per kind).
5. **Sidebar "Affects" line**: in `changed-methods` mode
   (`renderChangedMethods` in `static/app.js`), each rendered changed
   method gets one compact line naming its enclosing class (if any, with
   its status chip) and any variables reached via its outgoing `uses`
   edges (name + status chip) — this is what actually answers "what else
   does this touch" without a separate click, closing the gap this ADR
   exists to close.

## Alternatives considered

- **Compute referenced-globals text at render time, no graph nodes** —
  cheaper: no new symbol kind, no new edge kind, no layout/status
  plumbing. Rejected: it can't be colored on the graph itself, so a
  reviewer can't see "this global changed *and* three unrelated changed
  methods now touch stale state" as a structural fact — exactly the
  blast-radius promise docs/02 makes, which is about coloring
  affected-but-unchanged nodes on the graph, not describing them in a
  text blurb next to one method.
- **Fold variable references into the existing `calls` field/edge kind**
  instead of adding `uses` — less new code (no second field, no second
  edge kind). Rejected: it blurs "calls" to mean "references," which
  breaks the calls-edge panel's caller/callee framing (ADR 017 shows
  caller/callee code under the heading "Calls collapsed onto this edge")
  for edges that aren't calls at all. The extra field/edge kind is a small
  price for keeping "calls" meaning what it says.
- **Track instance attributes (`self.x = ...`) as class-level state too**
  — closer to what "class variable" means colloquially. Rejected for v1:
  distinguishing a genuine instance-attribute assignment from a local
  variable that happens to be named `self.x` in some other binding shape,
  or catching every method that *reads* an instance attribute nobody in
  that class ever assigns at class-body level, needs real data-flow
  reasoning, not a name match — likely noisy without evidence it's needed
  yet (see Out of scope).

## Consequences

- Every existing per-symbol code path (status, diff, rationale mining,
  code view) picks up `variable` symbols automatically, since none of
  them special-case `kind` — confirms the `FileIndex`/`SymbolInfo`
  contract (CLAUDE.md invariant) already generalizes to "any named,
  independently-diffable unit," not just callables. No invariant is
  touched: still Python-everywhere/JS-only-in-`static/`, still no
  hunk-to-symbol mapping (a `variable` symbol's span is still a whole
  AST-node-to-whole-AST-node diff, same as every other symbol kind), no
  new backend dependency.
- A class already turning `modified` when a method inside it changes is
  existing, unchanged behavior — this ADR surfaces it in the
  changed-methods panel rather than changing when it happens.
- Adds one more edge kind and one more node kind to `static/app.js`'s
  rendering surface, following the same pattern `calls`/`imports` already
  established (ADR 013's per-kind visibility toggle).
- Cross-file `uses` resolution inherits whatever `calls` edges already do
  (same shared-tree/import-reachability functions, reused not
  reimplemented) — nothing new to design there.

## Out of scope

- Instance attributes (`self.x = ...`) as class-level variables — revisit
  with real dogfood evidence; likely needs its own decision once the
  false-positive/false-negative rate of a name-match heuristic is known.
- Read/write distinction on a `uses` edge (only "references," not
  "assigns to" vs. "reads from") — v1 treats all references uniformly.
- Non-Python domains: variables are a Python-specific AST concept; the
  Markdown extractor (ADR 046) is untouched by this decision.
- Any change to `graphwerk/staging/differ.py` — confirmed above that none
  is needed; the differ's qualname-generic loop already handles the new
  symbol kind.
