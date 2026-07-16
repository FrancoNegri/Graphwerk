# 054. Relative imports resolve using their dot-level, not a bare module name

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md

## Bug

`from .models import X` in `src/agendabot/bsp/twilio.py` produces no
`imports` edge to `src/agendabot/bsp/models.py` at all — confirmed live
against the agendabot dogfood graph (`/api/graph`), and the reason both
files sit at layer 0.

Root cause, two compounding steps:

1. `_imported_modules` (`graphwerk/indexing/python_ast.py:68-71`) reads
   `node.module` off an `ast.ImportFrom` but ignores `node.level` (the
   dot-count marking a relative import). `from .models import X` and an
   absolute `import models` both collapse to the same bare string
   `"models"` — the relative import loses the information that would make
   it unambiguous.
2. `ModuleFileResolver.resolve()` (`graphwerk/service.py:44-48`) looks that
   bare name up by dotted-path *suffix*, and this repo has two files whose
   suffix is `models` — `src/agendabot/bsp/models.py` and
   `src/agendabot/models/__init__.py` (a real package). Two suffix matches
   means `resolve()` returns `None` and the edge is silently dropped.

Any relative import whose target name collides with an unrelated
same-named module elsewhere in the tree hits this same silent drop — not
specific to `bsp/twilio.py`.

## Fix direction

`_imported_modules` already has everything it needs to sidestep the
suffix-ambiguity problem entirely for relative imports: given the
*importing file's own* `rel_path`, a relative import's true dotted target
is computable directly (strip the importer's own trailing module segment
for level 1, one more segment per additional level, then append
`node.module` if present) — the same dotted-path convention
`ModuleFileResolver` already builds from `rel_path` for its exact-match
table. Producing that fully-qualified dotted string at extraction time
means relative imports resolve via `ModuleFileResolver`'s existing
*exact*-match branch, not its ambiguous suffix search — no resolver change
needed, and absolute imports (`level == 0`) keep today's behavior
untouched.

## Acceptance criteria

- `PythonAstExtractor.extract` on a fixture package (real temp files, per
  this skill's fixture preference) where a module does
  `from .sibling import X` produces a `FileIndex.imports` entry equal to
  the sibling's fully dotted path (e.g. `pkg.sub.sibling`), not the bare
  `sibling`.
- Same for `from ..other import X` (level 2) resolving up one additional
  package level, and for `from . import X` (`node.module is None`,
  level 1) resolving to the current package's own dotted path.
- Absolute imports (`import foo`, `from foo.bar import X`, `level == 0`)
  are unaffected — same `FileIndex.imports` contents as before this
  ticket.
- End-to-end: with a fixture tree reproducing the ambiguous-suffix
  situation (two files both named/suffixed `models`, one imported
  relatively from a third file), `GraphService.snapshot()` produces the
  `imports` edge for the relative import, and the two same-named files are
  no longer forced onto the same layer by a missing edge.
- Existing `ModuleFileResolver` tests for absolute/suffix resolution still
  pass unmodified — this ticket doesn't touch `resolve()`.

## Likely files

- `graphwerk/indexing/python_ast.py` — `_imported_modules` (needs the
  importing file's `rel_path` and `node.level`; signature change,
  `extract()` is its only caller).
- `tests/indexing/test_python_ast.py` (or wherever indexer tests live —
  create alongside if this is the first indexer test file) — relative
  import fixtures.
- `tests/test_service.py` (or equivalent) — end-to-end ambiguous-suffix
  fixture if not already covered at the indexer level.

## Out of scope

- Any change to `ModuleFileResolver.resolve()` or its suffix-matching
  behavior for absolute imports — untouched by design.
- `TYPE_CHECKING`-guarded imports, `importlib`/dynamic imports, or
  `sys.path` manipulation — out of scope for the AST-level extractor, same
  as today.
- Star imports (`from .models import *`) — already unresolved to specific
  symbols before this ticket; not made worse or better here.
