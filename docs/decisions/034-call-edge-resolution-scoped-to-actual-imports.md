# 034. Call-edge resolution scoped to the caller's own file or its actual imports

Status: accepted
Date: 2026-07-17

## Context

Phase 2's real-repo hardening goal (docs/04-roadmap.md) is to fix what the
differ/indexer trips on during dogfooding — the same goal that produced
ADR 032. Live on the current agendabot dogfood graph
(`~/projects/agendabot` / `~/projects/agendabot-graphwerk-staging`), a
reviewer spotted `src/agendabot/trace/e2e_runner.py::run_e2e_scenario`
(status `affected`) wired by a `calls` edge to
`src/agendabot/conversation.py::_format_history` (status `added`), even
though `e2e_runner.py` itself has zero diff — not even its imports
changed.

Traced against the actual staged source: `e2e_runner.py` defines its own
local `_format_history(entries, max_entries)` and calls exactly that one
(`_format_history(history_entries, config.history_length)`); it does not
import anything from `conversation.py` at all. `conversation.py`'s
`_format_history` is an unrelated, newly-added function that only shares
the simple name. The edge is a phantom — these two functions have never
been in a caller/callee relationship in any version of the code.

Root cause: `GraphService._add_call_edges` resolves each caller's called
names via `name_to_ids`, keyed purely by **simple, unqualified name**
(`qualname.split(".")[-1]`) — so any two symbols anywhere in the repo that
happen to share a name collide as candidate targets. ADR 032 already
narrowed this once, by requiring the candidate to share a parsed tree with
the caller (killing cross-tree deleted/added phantom pairs), but that
filter does nothing here: both `run_e2e_scenario` (effectively
`unchanged`/non-deleted) and `conversation.py::_format_history` (`added`)
are valid same-tree candidates under ADR 032's rule. The gap is one level
more specific than tree membership: **reachability**. Python name
resolution means a caller can only actually reach a symbol defined in its
own file or in a module it imports — `_add_call_edges` doesn't model that
at all, unlike `_add_import_edges`, which already resolves each file's
declared imports to concrete target files via `ModuleFileResolver`.

This isn't a one-off: any two functions/methods anywhere in a repo sharing
a simple name (common for small helpers — `validate`, `_format_history`,
`__init__`-adjacent patterns) will wire together the same way, regardless
of whether either file can actually see the other.

## Decision

Reuse the same `ModuleFileResolver` `_add_import_edges` already builds
(resolves a module name to the concrete file that defines it, tolerating
src-layout roots) to scope `_add_call_edges`'s candidate targets: a caller
in file F may only resolve a called name to a target defined in F itself
or in a file that F's relevant tree (base or staged, per the existing
ADR 032 caller-status branch) actually imports. Concretely, for each file,
compute the set of files reachable via its imports (module name ->
resolved file, dropping unresolved externals), and intersect that with the
existing ADR 032 tree-membership filter before wiring an edge — both
constraints apply together, neither replaces the other.

## Alternatives considered

- **Prefer a same-file candidate when one exists, otherwise fall back to
  the current any-match behavior** — cheaper (no import-resolution wiring
  into `_add_call_edges`), but only patches the collision where a decoy
  exists in a third file while the real target is local; a same-repo
  collision between two *different* files neither of which is the
  caller's own (plausible in a bigger repo) still phantom-wires exactly as
  today. Rejected — it narrows the bug's odds without closing the class of
  bug, and the correct resolution data (`ModuleFileResolver`) already
  exists and isn't meaningfully more expensive to apply here too.
- **Do nothing / document as a known limitation** — zero cost, but leaves
  a confirmed, live phantom edge that actively misleads a reviewer (marks
  an untouched function `affected` for a call that never happened),
  undermining exactly the "does the stated intent match what the code
  does" trust docs/02 says the tool exists to build. Rejected.

## Consequences

- Closes the phantom-edge class demonstrated on the agendabot dogfood
  graph: a caller can no longer resolve to a same-named symbol in a file
  it neither owns nor imports.
- `_mark_affected` (blast radius) gets more precise as a side effect, same
  shape as ADR 032's note: an unchanged/affected node can no longer appear
  "affected" via a call it never actually made.
- Slightly more coupling between `_add_call_edges` and `_add_import_edges`
  (both now depend on `ModuleFileResolver` / each file's resolved import
  set) — acceptable; they're both already file-import-aware operations on
  the same `changes` data, and the resolver itself is unchanged.
- No new invariant touched: still comparing already-parsed `FileIndex`
  data (`imports`, `symbols`) across the two trees, no hunk-to-symbol
  mapping, no new backend dependency, no model change.

## Out of scope

- Wildcard imports (`from x import *`) and dynamically resolved calls
  (`getattr`, decorators, metaclasses, monkeypatching) — Python's true
  call graph is undecidable in general; this only tightens resolution
  using the static import list already extracted, the same limitation the
  rest of the tool already accepts.
- Relative-import dot-level resolution — separately tracked, ticket 054.
- Symbol-move detection / reunifying a relocated symbol's old and new
  identity — stays deferred per ADR 032.
- Any change to `_add_import_edges` itself or to ADR 033's import-edge
  status work — this decision only reuses `ModuleFileResolver`, doesn't
  modify it.
