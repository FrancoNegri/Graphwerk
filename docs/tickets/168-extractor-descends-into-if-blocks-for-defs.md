# 168. Symbol extraction descends into `if` blocks for function/class defs

Status: done
Decision: none — bug fix, no invariant touched (north-star scoping session,
2026-07-21; see Context below in lieu of an ADR)

## Goal

`PythonAstExtractor.extract` indexes module-level functions/classes nested
inside `if` blocks (e.g. `if TEST_MODE: def configure_calendar_slots():
...`), so these symbols — and any `calls`/edges they produce — participate
in the differ instead of being permanently invisible in both base and
staged trees.

## Context

Dogfooding report (agendabot, live working tree, 2026-07-21): a `calls`
edge from `webhook.py` to `dependencies.py::get_calendar` disappeared with
no `deleted` signal anywhere in the graph. Root cause, confirmed against
the live `:8135` server: the calling function, `configure_calendar_slots`,
was itself deleted in the uncommitted diff — but it was defined inside
`if TEST_MODE:` in `webhook.py`, and `PythonAstExtractor.extract`'s symbol
pass (`graphwerk/indexing/python_ast.py:40`, `for node in tree.body`) only
looks at direct top-level statements. The function was never a node in
*either* tree, in any prior render either — not `unchanged` before this
diff, not `deleted` now. There is nothing for the qualified-name differ to
mark, because the symbol was never a key in `FileIndex.symbols` to begin
with.

This is a narrower case than [ADR 024](../decisions/024-extract-nested-imports.md),
which widened the *imports* pass to the whole tree (skipping
`TYPE_CHECKING` guards) but explicitly left "top-level symbol extraction...
unchanged" as out of scope for that decision. It's also unrelated to
[ADR 059](../decisions/059-collapsed-container-deletion-visibility.md) /
ticket 167 (reverted 2026-07-21, "did not work as intended") — that one
addressed a *correctly-`deleted`* symbol getting masked by collapsed-pill
status ranking in `static/app.js`. Here the symbol never becomes a `deleted`
node in the first place, so there's no status to mask.

No architectural invariant is touched: this stays a qualified-name diff
over `FileIndex.symbols` (CLAUDE.md's differ model), adds no hunk-to-symbol
mapping, and mirrors a precedent that already exists in the same file (the
imports pass already descends into `if` blocks).

## Acceptance criteria

- A module-level `if`/`elif`/`else` block's direct body is walked for
  `FunctionDef`/`AsyncFunctionDef`/`ClassDef` the same way `tree.body`
  already is, recursively for nested `if`s — mirroring the existing
  `TYPE_CHECKING`-guard skip already used for the imports pass, so a
  `if TYPE_CHECKING:` block's defs stay excluded (they're not real
  runtime symbols).
- Explicitly scoped to `If` nodes only — do **not** reuse
  `_iter_executable_nodes` wholesale or otherwise descend into function/
  class bodies looking for nested defs (that would turn closures/local
  helpers into top-level symbols, a materially different and unscoped
  change).
- Class methods found this way get the same `Class.method` qualname
  treatment as today's top-level classes.
- New test: a function defined inside a module-level `if` block is indexed
  as a symbol, appears with the correct status when added/deleted/modified
  across base/staged, and its `calls` participate in edge construction.
- Existing test coverage for `TYPE_CHECKING`-guarded imports/defs is
  unaffected (defs inside a `TYPE_CHECKING` guard stay unindexed, matching
  the existing import-side behavior).

## Likely files

- `graphwerk/indexing/python_ast.py` — `PythonAstExtractor.extract`'s
  symbol-collection loop; probably a new small helper alongside
  `_iter_executable_nodes` (or a scoped variant of it) rather than reusing
  it directly, per the acceptance criteria above.
- `tests/indexing/test_python_ast.py` (or wherever extractor tests live) —
  new coverage for if-nested function/class defs.

## Out of scope

- Descending into function/class bodies for nested defs (closures/local
  helpers) — different, unscoped change; not what this ticket's dogfood
  finding needs.
- Ticket 167 / ADR 059's collapsed-pill masking problem — still open
  (the fix was reverted, not re-diagnosed), but it's a `static/app.js`
  aggregation bug, unrelated to this extraction gap. Leave for a separate
  pass.
- Any change to `_mark_edge_status`/ADR 054's deliberate non-signaling of
  calls removed from a `MODIFIED` (not `DELETED`/`ADDED`) caller — that's
  a different, already-adjudicated limitation (see ADR 054's rejected
  "propagate MODIFIED source status" alternative), not something this
  ticket revisits.
