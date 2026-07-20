# 051. Changed-methods code display mode

Status: proposed
Date: 2026-07-20

## Context

The sidebar code panel (`static/index.html:49-52`, `app.js` `codeDisplayMode`)
offers exactly two ways to view a selected node's code: `full` ("code +
changes" — the entire file or class body, every method included whether it
changed or not) and `changes-only` (only the bare added/removed lines, with
zero surrounding context). Dogfooding this against real sessions (docs/04
Phase 2's exit criterion: "build a graphwerk feature using graphwerk to
review it") surfaced that neither extreme is usable for a file or class with
one changed method among several unchanged ones: `full` buries the actual
change in unrelated code, `changes-only` strips out the context needed to
read the change at all.

This is exactly the gap docs/02's open question flags — "granularity of a
node for apply purposes: file, class, or function? function-level is the
vision" — except here it's the *code panel's* granularity, not apply's. The
graph already renders methods as their own nodes; the code panel should let
a reviewer see "just the method that changed," which is a structural-context
problem (docs/02: "the graph shows... which callers are affected", i.e. the
review surface should reflect the symbol structure, not just diff text).

## Decision

Add a third `code-mode` value, `changed-methods`, as a radio option between
the two existing ones ("code + changes" | "changed methods" | "changes
only"). When the selected node is a container (file or class) with changed
descendant symbols, this mode renders each changed leaf symbol (kind
`function`/`method`, status other than `unchanged`) using its own
already-computed full-context `code` view (the same per-symbol view already
shown when that symbol's own node is selected directly), stacked under a
small heading per symbol — instead of the container's single merged
file/class-wide view.

This is purely additive client-side logic in `static/app.js`: every symbol
node in the snapshot already carries its own independently-built `code`
field (`graphwerk/service.py:136-139`, one per qualname, diffed
symbol-against-symbol — not sliced out of the file's diff). "Changed
methods" mode just selects and concatenates the already-existing per-symbol
views for a node's changed children; it computes nothing the backend
doesn't already send.

When the selected node is itself a leaf (function/method) or a container
with no changed leaf descendants, `changed-methods` mode falls back to the
same rendering as `full` mode — there is nothing to narrow down further.

## Alternatives considered

- **Backend line-range slicing** — tag each line of the file-level `code`
  view with its enclosing symbol (via `SymbolInfo.lineno`/`end_lineno`) and
  filter to lines inside changed symbols while keeping full context. More
  precise (would also catch changes confined to class-level code outside
  any method), but this is exactly the hunk-to-symbol mapping
  `docs/03-architecture-notes.md` calls out as a hard problem the
  architecture deliberately avoids by diffing symbols independently
  instead. Rejected: it reintroduces the trap the current differ design
  sidesteps, for a display-only feature that doesn't need it.
- **New `/api/code_view?mode=` endpoint** — move the composition to the
  backend as a new API surface. Rejected: the data needed (per-symbol
  `code` views) is already in the existing `/api/graph` payload; adding a
  network round trip and backend code for something fully derivable
  client-side doesn't buy anything, and all other view-mode filtering
  already happens client-side (`app.js`'s `toElements()`,
  `changedAndBlastRadiusIds()`) — this stays consistent with that.

## Consequences

- Makes the code panel's granularity match the graph's already
  function/method-level node granularity, without touching the differ,
  models, or any backend module.
- No new invariant is touched: still Python-everywhere/JS-only-in-static/,
  still no hunk-to-symbol mapping, still `FileIndex`/`SymbolInfo` untouched
  and language-neutral (works for any future extractor, including the
  Markdown one from ADR 046, since it produces symbol-shaped nodes too).
- Makes it slightly harder to spot a change confined to class-level code
  outside any method (rare — e.g. a changed class attribute or decorator
  with no method body touched); see Out of scope.

## Out of scope

- Any change to `graphwerk/codeview.py`, `graphwerk/models.py`, or
  `graphwerk/service.py` — no backend/model work needed for this decision.
- Surfacing changes confined to class-level code outside any method (no
  changed method child) in `changed-methods` mode — falls back to `full`
  mode today; revisit if this proves common during Phase 2 dogfooding.
- The separate graph-level "changed + blast radius only" checkbox
  (`static/index.html:20-23`) — a different, already-shipped toggle
  controlling node visibility, not code panel content. Not touched here.
- Any wording/labeling decision for non-Python domains (e.g. whether a
  changed Markdown heading counts as a "method" in the UI label) — left to
  the ticket to decide; not an architectural question.
