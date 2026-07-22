# 181. `SymbolInfo.uses`: functions/methods record which variables they reference

Status: done
Decision: docs/decisions/062-variable-symbols-and-changed-method-blast-radius.md

## Goal

Every function/method `SymbolInfo` gains a `uses: set[str]` field
(parallel to `calls`) naming the module-level globals and own-class
attributes its body references, so `GraphService` (ticket 182) has
something to wire `uses` edges from.

## Acceptance criteria

- `graphwerk/models.py`: `SymbolInfo` gets `uses: set[str] =
  field(default_factory=set)`.
- A module-level function whose body references a module-level global by
  simple name (`ast.Name`, load or store context — e.g. `global _CACHE;
  _CACHE[k] = v` or a bare read `return _CACHE`) has that global's name in
  its `uses` set. Only names that are actually extracted as module-level
  variable symbols (ticket 180) in the same file count — an arbitrary
  free variable that isn't a tracked global is not added.
- A method whose body accesses `self.<attr>` where `<attr>` matches a
  class-level variable symbol (ticket 180) on its own enclosing class has
  `"ClassName.<attr>"` in its `uses` set. A `self.<attr>` access that
  doesn't match any class-level variable symbol on that class is not
  added (e.g. a genuine instance attribute, or a method call
  `self.foo()` — already covered by `calls`, must not also land in
  `uses`).
- A function/method that calls another function (`ast.Call`) is unaffected
  — `calls` extraction is unchanged, `uses` is strictly additive and only
  populated for variable-shaped references.
- Per ADR 062's own wording ("for each function/method, the set of simple
  names it references... plus `self.<attr>` attribute accesses..."), a
  **method**'s `uses` set is the union of both: module-level globals
  referenced by simple name (same rule as module-level functions) *and*
  `self.<attr>` accesses matching its own class's variable symbols — not
  only the latter.
- `uses` is empty by default for `variable`-kind symbols themselves (a
  variable doesn't reference anything) and for classes' own
  `_class_body_called_names`-derived symbol (out of scope — class-body-level
  `uses` is not required by this ticket, only function/method `uses`).

## Likely files

- `graphwerk/models.py` — new field.
- `graphwerk/indexing/python_ast.py` — extraction pass; needs the set of
  known module-level global names and, per class, the set of known
  class-level attribute names (both already produced by ticket 180) as
  context available.
- Extractor tests — new cases for `uses` population and the negative
  cases above (unmatched name, `self.method()` not counted).

## Out of scope

- Wiring `uses` into graph edges — ticket 182.
- Read/write distinction — ADR 062 explicitly defers this.
