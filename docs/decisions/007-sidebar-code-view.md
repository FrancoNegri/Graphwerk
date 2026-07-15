# 007. Sidebar code view: full source with diff overlay and syntax highlighting

Status: proposed
Date: 2026-07-14

## Context

The graph is the review surface (docs/02), but the sidebar — where the
actual reading happens — currently shows either a bare unified diff (hunks,
no surrounding code) or, for unchanged nodes, colorless plain text
(ADR 004). That is *less* context than an ordinary diff viewer gives, which
undercuts the product's core claim. Two user-requested upgrades, decided
together because they share one rendering path:

1. Syntax highlighting for any source shown in the sidebar.
2. Changed nodes show the **entire** file/class/function with the diff
   overlaid in place — full source, added/removed lines colored inline —
   instead of isolated hunks.

## Decision

Build the view server-side, ship it in the snapshot, keep JS a painter
(the ADR 005 pattern). All stdlib.

1. **Token highlighting** (`tokenize`, stdlib): classify Python source into
   per-line spans — `(start_col, end_col, class)` with classes like
   keyword / def-name / string / comment / number. On tokenize failure
   (mid-edit syntax errors — the ticket 008 reality) or non-Python text,
   fall back to zero spans: plain but never broken. New languages later
   bring their own classifier alongside their extractor.
2. **Merged line view** (`difflib.SequenceMatcher`, stdlib): given the base
   and staged text of one node, produce the full ordered line list where
   each line is `context`, `added`, or `removed` — removed lines
   interleaved where they were. Added/deleted nodes degrade naturally to
   all-added / all-removed. Each line records which side and line number it
   came from.
3. **Combine**: context/added lines carry spans from highlighting the
   staged text, removed lines from the base text (so multi-line strings
   and other stateful tokens highlight correctly on both sides).
4. **Payload**: every `GraphNode` gains a `code` field — the line list with
   ops and spans; unchanged nodes get an all-context view of their source.
   The pair diffed is the node's own base/staged text: file text for file
   nodes, the already-qualname-matched symbol sources for symbol nodes
   (exactly the pairs `_symbol_diff` uses today). The `diff` field stays
   (the reject payload quotes it); the raw `source` field is dropped from
   the payload once the UI reads `code`, since `code` carries the text.
5. **Sidebar** replaces the separate diff/source sections with one code
   view: line numbers, red/green line backgrounds for removed/added, token
   colors on top. app.js maps span classes to CSS and escapes text; no
   parsing or diffing client-side.

Invariant note: this adds **no** hunk-to-symbol mapping. Change status
remains decided by the differ's qualname comparison; the merged lines are
computed per already-matched pair, for display only.

## Alternatives considered

- **Vendored highlight.js, client-side** — the vendoring path exists and it
  covers all languages, but it moves real logic into untested JS (against
  ADR 005 and the thin-JS rule), and the diff-overlay half still needs
  server data — so it only half-solves while splitting the logic across
  the boundary.
- **Pygments server-side** — better token quality than `tokenize`, but
  breaks the "fastapi + uvicorn only, stdlib otherwise" invariant for
  something stdlib covers, given only Python is indexed today.
- **Server-rendered HTML strings** — one compact field, but ships markup in
  JSON (escaping/XSS surface) and couples the backend to presentation
  class names; spans-as-data keeps the contract semantic.
- **On-demand `/api/code?node=` endpoint instead of snapshot embedding** —
  smaller `/api/graph` payload, but adds a second fetch path and state to
  the UI. Flask-scale measurements (959 nodes, ~1s snapshot with full
  source already embedded) say embedding is fine today; the endpoint is
  the recorded escape hatch if payloads bloat.

## Consequences

- Easier: reviewing a change in its full surroundings (the point of the
  product); consistent rendering for changed and unchanged nodes; ticket
  008's broken-file states degrade to plain-but-visible text; future
  languages slot in as classifier + extractor pairs.
- Harder: snapshot payload grows (spans roughly double the text weight);
  accepted at current scale, escape hatch noted above. Two highlight
  passes per changed node is negligible next to parsing.
- Invariants: all held — stdlib only, logic in Python under pytest, JS
  paints, differ untouched as the source of truth for status.

## Out of scope

- Non-Python syntax highlighting — Phase 5, arrives with tree-sitter
  extractors.
- Intra-line (word-level) diff emphasis — later polish on top of the same
  line model.
- Collapsing long unchanged regions in the code view — UX polish, revisit
  after dogfooding the full-source view.
- The on-demand code endpoint — only if payload size becomes a measured
  problem.
