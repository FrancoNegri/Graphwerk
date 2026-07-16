# 024. Extract imports from the whole file, not just the top level

Status: proposed
Date: 2026-07-16

## Context

With ADR 023 (tickets 063/064) landed, re-checking the agendabot graph
surfaced a third false-root case: `src/agendabot/calendar/google.py` and
`src/agendabot/db/store.py` both sit at layer 0, despite each having a real
importer — `webhook.py` imports both, at `webhook.py:241` and
`webhook.py:192` respectively. Both imports are **function-local**
(`from agendabot.calendar.google import GoogleCalendarAdapter` inside a
function body, not at module top level) — a normal pattern for deferring an
optional/heavy dependency (a Google Calendar SDK, a Postgres driver) or
avoiding a circular import.

`PythonAstExtractor.extract` (`graphwerk/indexing/python_ast.py`) only
iterates `tree.body` — the module's direct top-level statements — for both
symbol extraction and `ast.Import`/`ast.ImportFrom` collection. A nested
import, however deep, is invisible to `index.imports`, so `_add_import_edges`
never emits the edge, and the target file looks like a root regardless of
how it's actually reached. This is a different failure mode than ADR 023's
two fixes (which were about edges that exist getting mis-handled during
layering) — here, the edge is never created in the first place, at the
extraction layer.

The same repo also has the adjacent case that needs excluding on purpose:
`executor.py` guards `from agendabot.calendar.port import CalendarPort`
behind `if TYPE_CHECKING:` (`executor.py:11-12`) — a type-hint-only import
that never executes at runtime. Naively walking the whole tree for imports
would turn that into a fabricated "real" dependency edge, reintroducing a
false-edge problem while fixing a false-root one.

This is real-repo evidence discovered by the same graph-evaluation request
that drove ADR 023, in the same phase (Phase 2 dogfooding, docs/04) and
serving the same "is this near where the app starts" structural-context
promise (docs/02).

## Decision

In `PythonAstExtractor.extract` (`graphwerk/indexing/python_ast.py`),
collect `imports` from the entire function/class body tree, not just
`tree.body`, while skipping the body of any `if TYPE_CHECKING:` /
`if typing.TYPE_CHECKING:` block. Concretely: walk the full tree collecting
every `ast.Import`/`ast.ImportFrom` node, except don't descend into an
`ast.If` node whose test is a `Name`/`Attribute` reference literally named
`TYPE_CHECKING`. Top-level symbol extraction (`tree.body` for
functions/classes) is unchanged — this only widens where `imports` looks.

`index.imports` stays the same `set[str]` shape (`FileIndex`'s existing
contract) — no model change, no new field. `_add_import_edges` and
everything downstream (ADR 023's fix included) consume it exactly as today.

## Alternatives considered

- **Leave it top-level-only (status quo)** — simplest, but is the direct
  cause of this dogfood finding: any lazily-imported dependency (a common,
  intentional pattern for optional/heavy imports and circular-import
  avoidance) becomes an invisible edge and its target a false root.
  Rejected.
- **Walk the whole tree unconditionally (no `TYPE_CHECKING` exclusion)** —
  smallest possible diff, but the same repo already shows this fabricates a
  runtime dependency edge out of a type-hint-only import, which would
  misplace `calendar/port.py` relative to `executor.py` the same way the
  false roots this ADR fixes misplaced things the other direction. Rejected
  — trading one false-edge class for another isn't a fix.
- **Whole-tree walk with `TYPE_CHECKING` exclusion (chosen)** — matches
  what the import actually means at runtime: a lazy/deferred import is a
  real dependency (it executes, eventually); a `TYPE_CHECKING`-guarded one
  never does.

## Consequences

- `calendar/google.py`, `db/store.py`, and any other file reached only
  through a function-local import get a real (non-zero) layer.
- Files imported *only* inside `TYPE_CHECKING` blocks continue to show no
  edge from that import — unchanged from today, since today's top-level-only
  walk already misses them too; this decision only widens what's captured
  for *executable* imports.
- `index.imports` remains a flat set of module names with no positional/
  conditional metadata — a file that both top-level-imports and
  lazily-imports the same module is indistinguishable from one that does
  either alone. No evidence this repo needs that distinction.
- Touches the `FileIndex`/`SymbolInfo` contract's *fidelity*, not its
  shape — consistent with the invariant that it stays the language-neutral
  extraction contract; this is a Python-extractor internal fix, not a
  model change.

## Out of scope

- `try:`/`except ImportError:` optional-dependency imports — these do
  execute (at least the `try` branch attempt), so the whole-tree walk
  already captures them like any other nested import; no special-casing
  needed or evidenced.
- Any change to `_called_names` or call-edge extraction — this ADR is
  imports-only.
- Re-litigating ADR 023's fixes — this is a third, independent gap found
  in the same evaluation pass, not a revision of the other two.
