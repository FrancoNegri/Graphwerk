# 006. Rationale mining v2: whole-transcript mention attribution

Status: proposed
Date: 2026-07-14

## Context

Per-node rationale is a core concept feature (docs/02): it turns review into
"does the stated intent match the code?" and gives rejections something to
attack. The current miner (`graphwerk/rationale/miner.py`) implements the
docs/03 primary mechanism naively: the last assistant text block before each
Edit/Write call becomes that file's "why", latest write wins.

The Phase 2 dogfood run (ticket 007) showed this failing in a real session:
the agent narrated one short lead-in sentence, then batched six edits, so all
six files carried the same weak line — while the genuinely useful per-file
rationale sat in the session's final wrap-up summary, which the miner never
reads. The roadmap pulled this forward from Phase 5 ("needed sooner than
polish") and flagged the redesign as a north-star decision. It also matters
for Phase 3: reject payloads quote the node's rationale ("you said X, but the
code does Y"), so weak rationale weakens the whole reject loop.

## Decision

Replace "last narration before the edit" with **whole-transcript,
mention-based attribution**, still fully deterministic and stdlib-only:

1. **Parse the transcript once** into an ordered list of assistant text
   *segments* (text blocks split into paragraphs and bullet lines) plus the
   edit events (which staged-relative paths were touched, and where in the
   segment order each edit happened).
2. **File-level attribution:** for each edited file, the rationale is the
   *latest* segment that mentions the file — by relative path, basename, or
   stem as a distinct token. Later-wins means a session's wrap-up summary
   ("- `cli.py`: added `--version` flag") naturally dominates earlier
   planning chatter, which is exactly what the dogfood run showed we want.
3. **Symbol-level attribution:** a segment that mentions a changed symbol's
   name (final qualname component, as a distinct token) becomes that
   symbol's rationale under the existing `rel::qualname` key shape. If the
   same name exists as a changed symbol in multiple files, the segment must
   also mention the file to count.
4. **Fallback chain** (most specific available wins):
   qualname mention → file mention → the current preceding-edit narration
   heuristic → nothing. The sidecar still overrides everything, unchanged —
   it remains the integration point for a future summarization pass.

`RationaleStore.why_for(rel, qualname)` keeps its signature; the service and
UI don't change.

## Alternatives considered

- **Post-hoc Haiku summarization** (docs/03 mechanism 2) — uniform one-line
  whys, but adds an LLM invocation path (a new dependency or a `claude -p`
  shell-out), cost, latency, and nondeterminism that resists pytest. The
  dogfood evidence shows the needed text already exists verbatim in the
  transcript; attribute it before paying to regenerate it. Revisit in
  Phase 5 via the sidecar if attribution quality proves insufficient.
- **Explicit `explain_change` annotation tool** (docs/03 mechanism 3) —
  taxes the agent, forgettable, breaks "works with a stock session";
  docs/03 already ranks it last. Still the fallback of record.
- **Keep the heuristic, mine only the final summary** — cheaper, but
  sessions don't reliably end with a summary, and mid-session narration is
  often the only source for files the summary skips; attribution over the
  whole transcript subsumes this.

## Consequences

- Easier: reviewers get per-file (and often per-symbol) whys from stock
  sessions; Phase 3 reject payloads quote sharper rationale; everything is
  deterministic and unit-testable (thin-JS rule: all logic in Python).
- Harder: mention matching can misattribute (a file named in speculation
  rather than explanation). Later-wins and token-boundary matching bound
  the risk; rationale remains review *assistance*, never verified truth
  (docs/03 caveat stands).
- Invariants: untouched — no new backend deps, no Node-side logic, no
  differ/model changes, worktree never intercepted.

## Out of scope

- LLM summarization pass — Phase 5, integrates via the existing sidecar.
- Showing multiple candidate rationales or a confidence indicator in the
  UI — revisit only if misattribution shows up in dogfooding.
- Multi-intent edits (refactor + fix in one change) — accepted caveat per
  docs/03.
- Rationale for non-Python files — arrives for free once ticket 009 gives
  those changes nodes; nothing rationale-specific to do here.
