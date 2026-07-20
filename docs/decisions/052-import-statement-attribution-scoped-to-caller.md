# 052. Import-statement attribution scoped to the admitting call site

Status: proposed
Date: 2026-07-20

## Context

ADR 038 made the calls panel's "admitting import" entries render the real
import statement text, and flagged a known fidelity limit up front: `
FileIndex.import_statements` keys by module name, and "if several
statements import the same module, the first one wins... revisit only if
dogfooding hits it."

Dogfooding this exact panel against the agendabot dogfood server hit it.
`_apply_adapter_resets` moved from `webhook.py` into a new `conversation.py`
during a session; `webhook.py` re-exports it for backward compatibility.
`tests/test_webhook.py::TestAdapterResets._call` admits the call via a
locally-scoped `from agendabot.webhook import _apply_adapter_resets` at its
own line 717 — but the same file also imports `agendabot.webhook` at the
top of the file (line 18, unrelated names: `BusinessConfig,
_resolve_business, app, get_bsp, get_claude, get_store`) and in several
other test methods. First-wins means `import_statements["agendabot.webhook"]`
resolves to line 18, so:

- `_statement_in_caller_span` (`graphwerk/service.py`) checks line 18
  against `_call`'s span — false — so `in_caller_code` is wrong: the entry
  isn't suppressed even though the real admitting statement genuinely sits
  inside the caller's own already-visible code (ADR 039's whole point).
- `_statement_code_lines` renders line 18's statement as the thing that
  "admits" this call — a statement that doesn't even name
  `_apply_adapter_resets`. Wrong information on the review surface, not
  just a cosmetic duplicate.

Net effect on this call pair: 4 rendered blocks (2 code sections + 2
import entries) where there should be 3 (2 code sections + the one
legitimate multi-hop chain entry into `conversation.py`, which is a
different file's import and correctly not suppressed). This is exactly
the kind of misleading-review-surface failure ADR 038's rationale exists
to prevent ("a review surface that paraphrases code invites exactly the
'go read the file to check' round-trip it exists to remove") — except now
it's not a paraphrase, it's an unrelated statement.

## Decision

Capture every import statement per module, not just the first, and pick
the one that actually applies to the caller being rendered:

1. **`FileIndex`** (`graphwerk/models.py`): `import_statements` becomes
   `dict[str, list[tuple[str, int]]]` — module name → every
   (verbatim statement text, start line) pair found for that module, in
   file order. The extractor (`graphwerk/indexing/python_ast.py`) appends
   instead of first-wins.
2. **`graphwerk/service.py`**: `admitting_entry` picks, for a given
   `caller_symbol`, the first statement in the module's list whose span
   (`_statement_in_caller_span`, unchanged logic) falls inside the
   caller's own `lineno..end_lineno` — reusing the existing containment
   check ticket 065 already established for nested imports. If none of
   the module's statements are inside the caller's span (the common case:
   a plain top-of-file import), fall back to the first statement, same as
   today. `in_caller_code` becomes true exactly when a caller-scoped match
   was found.
3. When `admitting_entry` is called with `caller_symbol=None` (the
   multi-hop chain's later hops, ADR 048/137 — the statement lives in a
   different file than the caller entirely), it keeps using the first
   statement — there is no caller span to match against in another file.

## Alternatives considered

- **Do nothing (accept the known limitation permanently)** — ADR 038
  explicitly deferred this pending dogfeed evidence; this is that
  evidence. Rejected: the failure mode isn't "less precise," it's
  actively wrong (an unrelated import rendered as if it admits a
  specific call), which is worse than the module-name-only fallback ADR
  038 replaced.
- **Change "first wins" to "innermost scope wins" globally, still one
  statement per module** — doesn't work: two different callers in the
  same file can each have their own distinct local import of the same
  module (exactly this case — `test_webhook.py` re-imports
  `agendabot.webhook` locally in half a dozen unrelated test methods for
  different names). A single winner can never be right for all of them
  simultaneously; the fix has to be caller-scoped, which requires keeping
  the full list.
- **Frontend heuristic (search `node.code` text for the import line)** —
  no backend change, but the frontend never receives full file source,
  only the pre-selected code views already assembled server-side; there's
  nothing for it to search, and it would violate the thin-JS rule (logic
  stays in Python, ADR 005) for what is fundamentally a data-modeling
  question (which statement is this).

## Consequences

- `FileIndex.import_statements` grows from `tuple` to `list[tuple]` per
  module — a mechanical, language-neutral extension (any extractor can
  emit a one-element list and degrade to today's behavior).
- The agendabot `TestAdapterResets → _apply_adapter_resets` pair goes
  from 4 rendered blocks to 3: the spurious/wrong caller-side entry
  disappears (suppressed as `in_caller_code: true`, matching the real
  nested import), the legitimate `conversation.py` chain-hop entry
  remains.
- No invariant touched: still no hunk-to-symbol mapping (this is
  statement-to-symbol-span matching, the same class of check ticket 065
  already introduced), `FileIndex`/`SymbolInfo` stay language-neutral, no
  new dependency, Python-side logic with JS staying a payload consumer.

## Out of scope

- Full Python scope resolution (shadowing, `as` aliasing across scopes) —
  span containment is a heuristic, same as ticket 065's; a caller-scoped
  match that's technically shadowed by an intervening scope is not
  handled. Revisit only if dogfooding hits it, same posture as ADR 038.
- The multi-hop chain hop's own statement selection (a hop whose caller
  lives in a different file) — unaffected, still first-wins, since there
  is no caller span in that file to match against.
- Any change to the imports-edge panel (`showEdgeImports`) — unaffected,
  same deferral as ADR 038/039.
