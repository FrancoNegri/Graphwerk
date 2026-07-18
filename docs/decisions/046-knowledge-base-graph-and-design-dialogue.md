# 046. Knowledge-base graph and design dialogue, via the existing pipeline

Status: proposed
Date: 2026-07-18

## Context

Every decision graphwerk has shipped so far reviews work *after* it's
generated: a session runs, a deterministic check gate validates it (ADR
040/044/045), and the human reviews the result on the code graph. Nothing
in the product touches the step *before* generation — deciding what to
build in the first place. That step happens today only as a side channel:
a human and Claude talk in a plain chat session (this very `north-star`
skill), hand-writing ADRs to `docs/decisions/` and tickets to
`docs/tickets/`, entirely outside graphwerk's own UI.

User call (2026-07-18): graphwerk should carry this as a general product
capability — "when graphwerk is used in a product it generates a knowledge
base... that keeps track of all the important decisions of the product,"
reviewed as a graph, with the same dialogue-then-apply loop the code side
already has, before tickets are handed to implementation.

This is explicitly a **detour** from the roadmap's stated next phase
(Phase 4, apply semantics — symbol-level apply, change-dependency edges,
conflict detection). The user chose to proceed with it now anyway; Phase 4
is not abandoned, just deferred behind this.

## Decision

Don't build a second, bespoke "docs graph" product surface. **Generalize
the existing one.** Every piece this needs is either already an invariant
or already built for the code side:

1. **Markdown extractor** (`graphwerk/indexing/markdown.py`), implementing
   the same contract `PythonAstExtractor` does: `extract(file_path, rel_path)
   -> FileIndex`. Each `##`-or-deeper heading becomes one `SymbolInfo`
   (`kind="heading"`, `qualname=`heading text, deduplicated if repeated),
   the section body between it and the next heading of equal-or-shallower
   level is its `source`. Stdlib-only (line-based heading scan; no
   CommonMark dependency — see Alternatives). This is literally the
   invariant in action: "`FileIndex`/`SymbolInfo` is the language-neutral
   contract — new languages are new extractors, not new models."

2. **Wire it into the walk/index path.** `graphwerk/indexing/walk.py`
   currently only enumerates `.py` files (`iter_python_files`); `.md` files
   fall into the same invisible bucket ticket 009 already flagged for
   *all* non-Python files. This decision closes that gap specifically for
   Markdown (not "any file" — see Out of scope), by extension-dispatching
   to the matching extractor.

3. **Cross-doc reference edges.** ADRs and tickets already cross-reference
   each other with plain relative Markdown links (`[044](../decisions/
   044-....md)`, `Decision: docs/decisions/046-....md`). Parse those
   deterministically into a new `references` `GraphEdge.kind` (alongside
   the existing `"calls"`/`"imports"`), reusing the edge-rendering
   machinery already in the graph. This is what makes it *a graph* and not
   just a folder of boxes — an ADR's tickets, and a ticket's ADR, become
   visible edges.

4. **One repo, one running graphwerk — not two instances.** `graphwerk
   start --repo <path>` already covers the whole repo, code and docs alike.
   `GraphNode` gains a `domain` field (`"doc"` for files the Markdown
   extractor indexed, `"code"` for everything else) — a direct readout of
   ticket 125's per-extension dispatch, not a new classification. The UI
   gets one **mode toggle, "Design" / "Implementation,"** doing double
   duty:
   - it filters the rendered graph to that domain's nodes/edges (same
     family as the existing changed-only/hide-tests toggles — render-only,
     ADR 005);
   - it's sent as the `scope` of the *next* spawned session.

5. **The hard boundary is enforced, not just suggested.** A session
   started with `scope="design"` may only `Edit`/`Write` `.md` paths; one
   started with `scope="implementation"` may not touch `.md` paths at all.
   This is enforced with a Claude Code **PreToolUse hook** — already
   named in docs/03 as a legitimate fallback ("can intercept and deny
   Edit/Write... useful as a signaling channel") — configured into the
   staged worktree before spawning, running a small stdlib glob check
   against the tool call's target path. A denial is a normal permission
   refusal the agent already knows how to react to; nothing is silently
   redirected, so the "never intercept/absorb writes" invariant (whose
   actual concern is staged writes going stale under the agent) isn't
   touched — the write simply doesn't happen.

6. **A real back-and-forth, not another one-shot.** "Hammer the design
   decisions" needs turns that share context. `SessionRunner.resume()` and
   the `--resume <session_id>` machinery already exist (ADR 040) but are
   only invoked internally, on check failure. Expose it as a user-triggered
   action: `SessionCycle.continue_session(prompt)` (requires a terminal
   state and a stored session id, resets check-cycle bookkeeping the same
   way `start()` does, then calls `runner.resume(prompt)`); `/api/prompt`
   gains an optional `continue_session: bool` field dispatching to it. The
   UI gets one additional affordance — "continue" alongside "new session"
   — no chat log, no message history view. ADR 011's explicit "kickoff-
   only, no chat log" stance for the *code* session stands; this only adds
   the ability to keep talking to the *same* session, which is a control,
   not a transcript surface.

7. **Docs.** `docs/02-product-concept.md` gains a short section naming
   this as a second review domain (design/decision knowledge base,
   alongside code) so future `north-star` passes see it as part of the
   concept, not a one-off. `docs/04-roadmap.md` gets an annotated,
   pulled-forward bullet (same pattern already used for ADR 011/040).

## Alternatives considered

- **A bespoke second product surface** (its own page, its own diff/apply
  model for docs) — duplicates the differ, the apply engine, the session
  machinery, and the rationale mining, all for a domain that fits the
  existing `FileIndex`/`SymbolInfo` contract just fine. Rejected: costs
  the most code for the least new capability.
- **Full CommonMark parsing** (`markdown-it-py`/`mistune`) for the
  extractor vs. a stdlib line-based heading scanner — a real parser buys
  nested structure and table/list awareness we don't need at
  heading-granularity, at the cost of the first new backend dependency
  (CLAUDE.md: "backend deps stay minimal... stdlib otherwise"). Rejected
  for v1; revisit only if heading-level granularity proves too coarse.
- **Semantic/LLM-inferred relationships** between docs (which ADR relates
  to which ticket, by meaning) instead of link-parsing — nondeterministic,
  and the differ's whole model is "compare by qualified name across two
  parsed trees, no fuzzy mapping" (CLAUDE.md invariant). ADRs and tickets
  already cross-reference by explicit relative link; parsing what's
  already there is free and deterministic. Rejected.
- **A full chat-log/threaded UI** for the dialogue vs. exposing `resume()`
  as a single "continue" control — ADR 011 deliberately scoped the prompt
  box to kickoff-only with no chat log; a transcript view is a bigger,
  separate surface, and the existing per-node rationale mining already
  makes prior-turn context visible on the graph. Rejected for this pass;
  the full multi-turn dialogue UI remains Phase 3's still-open half
  ("the human reject → re-prompt UI stays here", docs/04).

## Consequences

- No invariant touched, no new backend dependency, no new model classes —
  this is the multi-language invariant and the existing session/apply/
  check machinery, pointed at a second domain.
- No new architecture doc needed; extends docs/03's existing stack table
  implicitly (Markdown joins Python as an extractor).
- One repo, one running graphwerk instance — the design and implementation
  domains are views and session scopes on the *same* worktree pair, not
  separate invocations. Switching the mode toggle is enough to move
  between them; nothing needs restarting.
- The write boundary is a Claude Code permission-hook config graphwerk
  writes into the staged worktree per spawned session — an added
  responsibility for `SessionRunner`/`SessionCycle`, still stdlib-only,
  still one child process at a time.
- A ticket a design-scoped session produces is still copied into an
  implementation-scoped prompt by hand — this decision does not
  auto-chain the two; see Out of scope.
- `SessionCycle.continue_session` reuses `resume()`'s existing single-
  child-at-a-time semantics — no new concurrency surface.
- Heading-level granularity means a doc's prose changes inside one section
  render as one changed node, not paragraph-level — coarser than code's
  function-level apply, consistent with "smallest coherent v1."

## Out of scope

- Generalizing the walk/index path to *arbitrary* non-Python files
  (ticket 009's broader scope) — Markdown only, for this decision.
- Full CommonMark fidelity (tables, nested lists as sub-symbols, code
  fences as distinct nodes) — heading-section granularity only.
- Auto-chaining a knowledge-base session's generated ticket into a code
  session's prompt — stays a manual copy, as today.
- A visible chat-log/transcript UI — still Phase 3's open half.
- Any "check" analog for a knowledge-base session (linting docs, etc.) —
  `--check` stays optional and unset for this use case; no special-casing.
- Non-Markdown documentation formats (reST, plain text) — later, and
  trivially so: "new languages are new extractors."
