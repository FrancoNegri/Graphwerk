# 059. A class symbol's own `calls` excludes its methods' bodies

Status: proposed
Date: 2026-07-21

## Context

Dogfooding report (2026-07-21, live `:8135` server): a review showed both
`TestOnlyRouter -> get_calendar` (deleted) and
`TestOnlyRouter.__init__ -> get_calendar` (added) as separate `calls`
edges for what is, in the source, a single call site inside `__init__`.

Root cause, confirmed against `graphwerk/indexing/python_ast.py`:
`PythonAstExtractor.extract` builds a `SymbolInfo` for the class itself
(`kind="class"`) via `_symbol(node, node.name, "class", lines)`, and
`_symbol` computes `calls` with `_called_names(node)`, which does
`ast.walk(node)` over the *entire* `ClassDef` subtree — every method body
included. Each method already gets its own `SymbolInfo` with its own
`_called_names(child)`. The result: every call made inside any method is
counted twice — once attributed to the method (correct), once attributed
to the class itself (not a real relationship; classes don't call things,
their methods do). `service.py`'s edge builder treats every symbol,
class included, as an independent caller
(`symbol_calls[node_id] = info.calls`, `service.py:142`), so both
attributions become real, separately-statused `calls` edges in the
snapshot.

This directly undercuts two things the product concept and prior ADRs
already established:

- **"Blast radius for humans" / "change-dependency edges"** (docs/02): a
  reviewer reading the graph should see *what actually calls what*. A
  class node with its own outgoing `calls` edge to the same target its
  method already points at is not a second real relationship — it's
  noise that makes the graph lie about how many distinct call sites
  exist.
- **ADR 016 §2/§3**: "once several symbol-to-symbol `calls` edges
  collapse onto the same class/file representative pair," the reviewer
  clicks the collapsed edge to see the list of individual calls it
  stands for. With the class carrying its own duplicate raw edge, that
  list would show the same real call twice — once as the method's call,
  once as the phantom class-level one — actively contradicting the
  feature ADR 016 built to make this trustworthy. The two edges can also
  independently pick up different statuses (as in the dogfood report),
  since each is diffed from a differently-scoped source slice (the whole
  class body vs. just the method) — a visibly contradictory signal on
  the same rendered pair once ADR 055's severity-picking runs.

This is exactly the class of finding Phase 2 (docs/04) exists to catch:
"real-repo hardening... fix what the differ/indexer trips on." Not a
detour — on-phase.

## Decision

Scope a class-kind `SymbolInfo.calls` to calls made directly in the class
body, excluding anything inside a nested `FunctionDef`/`AsyncFunctionDef`
(a method). Concretely: compute it with a variant of `_called_names` that
walks the class subtree but does not descend into method bodies (mirrors
the same "the container's own code, not its nested defs' code" scoping
[[168](../tickets/168-extractor-descends-into-if-blocks-for-defs.md)]'s
`_iter_symbol_definitions` already applies one layer up, for which
statements count as top-level symbols in the first place).

Method-level `SymbolInfo.calls` is untouched — a method's own body walk
stays a full `ast.walk`, exactly as today.

The rare genuine class-body-level call (a class attribute default calling
a factory, a base-class expression, a decorator argument evaluated at
class-definition time) still gets attributed to the class symbol, since
those statements aren't inside a method body. Only method-body calls stop
being double-counted.

No change to `static/app.js`: once the backend stops emitting the
duplicate raw edge, ADR 016's existing collapse-time aggregation of
method-level edges onto a collapsed class representative becomes the
single, correct source for "this class (collapsed) calls X" — which is
exactly the behavior ADR 016 already describes, just no longer fighting
a second, backend-side source of the same signal.

## Alternatives considered

- **Dedupe at edge-construction time in `service.py`** (suppress a
  class-level edge to a target already covered by one of its methods) —
  keeps the extractor's aggregation and adds a second reconciliation
  rule downstream that has to stay in sync with it, plus edge cases (two
  different methods calling the same target legitimately collapse to one
  edge already — would the dedup rule tell that apart from the phantom
  case?). More coupling for the same result. Rejected.
- **Class symbols never carry `calls` at all** (always empty) — simpler
  one-line change, but throws away the rare legitimate class-body-level
  call case for no benefit over the scoped-walk approach, which costs
  barely more code. Rejected as slightly less complete for no real
  savings.
- **Recommended: scope `_called_names` for class symbols to skip method
  bodies** — smallest change that keeps the extractor's contract (a
  symbol's `calls` = what actually runs in that symbol's own code) honest
  for classes the same way it already is for functions, and requires no
  downstream reconciliation.

## Consequences

- A class's `calls` edges in the snapshot now only appear for genuine
  class-body-level calls (rare) instead of duplicating every method's
  calls.
- The "list what a collapsed edge represents" feature (ADR 016 §3) stops
  showing the same real call twice.
- No invariant touched: still a qualified-name diff over `FileIndex`/
  `SymbolInfo` (CLAUDE.md), no hunk-to-symbol mapping, Python-only change,
  no new dependency.

## Out of scope

- Any change to `static/app.js`'s collapse/aggregation logic (ADR
  016/055) — already correct once the backend stops double-emitting.
- Nested classes' own methods, decorator-call attribution nuances beyond
  "don't descend into method bodies" — same simple scoped walk handles
  whatever class-body-level code exists either way; no special-casing
  needed.
- Re-litigating whether a class should be a graph node/caller at all —
  out of scope, unchanged product decision.
