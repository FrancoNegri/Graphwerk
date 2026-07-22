# 188. `SymbolInfo.imports_used`: functions/methods record which module-level imports they reference

Status: done
Decision: docs/decisions/064-changed-method-code-view-surfaces-its-imports.md

## Goal

Each function/method `SymbolInfo` knows which module-level-imported names
(ticket 187's binding table) its own body actually references, excluding
names it binds itself — the per-symbol attribution ADR 064 renders as an
"imports used" block.

## Acceptance criteria

- `SymbolInfo` gains `imports_used: set[str] = field(default_factory=set)`,
  parallel to the existing `uses` field (ADR 062) — empty by default for
  `class`/`variable` kinds, populated for `function`/`method`.
- Computed the same way `_used_global_names` computes `uses`: an `ast.Name`
  load inside the function/method body whose `id` is a key in
  `FileIndex.imported_names` (ticket 187) is included.
- A name is excluded (not attributed) when the symbol itself binds it in
  its own scope: as a parameter, a local assignment target, a nested
  `def`/`class` name, or its own local `import`/`from...import` (any of
  these already render as part of the method's own source — attributing
  the outer module-level statement too would be a wrong/misleading
  duplicate, not just redundant).
- Verified against the dogfooded case in
  `src/agendabot/test_router.py::TestOnlyRouter.__init__`: `imports_used`
  includes the bindings for `APIRouter`, `datetime`, `Any` (referenced via
  the nested `_slot_from_config`'s return annotation and body) but not
  `BaseModel`/`ClassifierResult`/`_mock_intents`/`get_calendar` (all bound
  locally inside `__init__` itself).

## Likely files

- `graphwerk/models.py` — new `SymbolInfo.imports_used` field.
- `graphwerk/indexing/python_ast.py` — populate it alongside the existing
  `uses`/`calls` computation in `_symbol()`'s call sites.
- `tests/` — extend the existing extractor test module with cases mirroring
  the shadowing rules above (parameter shadowing, local assignment
  shadowing, nested-def shadowing, local-import shadowing).

## Out of scope

- Resolving what those statements' rendered text/status should look like
  on the API payload — ticket 189.
- Any change to `uses`/`calls` themselves.
