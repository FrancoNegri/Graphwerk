# Product Concept: Graph-Based Staging & Review for AI Code Changes

## The idea

A developer tool that inverts how AI-generated code changes are reviewed.

1. The app starts, reads a codebase, and renders it as an interactive graph (files, classes, functions; import and call edges).
2. The developer runs Claude Code — from a console or from the graph app's own prompt box — and asks for a feature as usual, in their one real working directory.
3. As Claude edits, the graph app diffs the working directory against the git ref it started from and updates live: **modified symbols in green, new ones in blue, deleted in red** (ADR 030).
4. Each changed file/class carries a **"why" explanation** — the rationale for the change, captured from the agent — shown when the node is selected.
5. The developer reviews at their own pace: what changed, where it sits structurally, and what it affects.
6. If a change looks wrong, the developer says so in the prompt box, which continues the same Claude session with that feedback (ADR 058).
7. When satisfied, the developer lands the change with their own plain git commit — or graphwerk's whole-tree "commit all" convenience, which is that same `git add`/`git commit` with no symbol-level staging in between (ADR 061). Either way it's a review lens over an ordinary git working directory, not a staging layer with a node-level apply/commit mechanism (ADR 058).

The graph is the review surface. Today's review surface for AI changes is a flat text diff (terminal prompt, Cursor's review pane, a PR); this replaces it with a structural view that shows *where* in the architecture the change lands and *what it touches*.

## Prior-art check (July 2026): appears to be novel

Searched for existing tools in this space. Findings:

- The entire "code graph + AI" ecosystem points in the **opposite direction**: graphs are built *for the agent* (context efficiency), while the human still reviews text diffs. [code-review-graph](https://github.com/tirth8205/code-review-graph) is the closest by name and even does blast-radius analysis — but its graph feeds the AI reviewer, not the human.
- Whole-codebase explorers (Sourcetrail, Understand, Emerge) have no AI-agent integration at all.
- No tool found that (a) visualizes an AI agent's live, uncommitted delta on a symbol graph, with (b) blast radius and (c) per-node rationale mined from the agent's own session, rather than a flat text diff.

**Symbol-level structural review of a live AI session, with rationale attached, is unclaimed territory.**

## What makes it more than a diff viewer

- **Structural context:** a diff shows text; the graph shows that the new `PaymentValidator` sits between `CheckoutService` and the gateway, and which callers are affected.
- **Blast radius for humans:** color affected-but-unchanged nodes (e.g., yellow = callers of a changed function) so the reviewer sees impact, not just edits.
- **Change-dependency edges:** the graph knows call edges, so it can draw dependencies *between changed nodes* ("this new class is useless without the call-site change over there") — visible before either half is committed. No flat diff can express this. This is the killer feature — see [03-architecture-notes.md](03-architecture-notes.md).
- **Per-node rationale:** every changed node explains *why* it changed, in the agent's own words. This turns review from "is this code correct?" into the stronger check "does the stated intent match what the code actually does?" — and a follow-up prompt can attack the reasoning directly ("your stated reason doesn't hold because...").
- **Targeted re-prompting:** telling the agent a specific change is wrong is a scoped follow-up in the same session (the prompt box, ADR 011), instead of re-running the whole request from scratch.

## A second review domain: the knowledge base, before the code

Everything above reviews code *after* it's generated. The same graph — the
same `FileIndex`/`SymbolInfo` contract, the same diff/session machinery —
also applies one step earlier, to the documentation that records *why* a
product is built the way it is: ADRs, tickets, a roadmap, whatever a
team's decision knowledge base looks like (ADR 046). A Markdown extractor
turns headings into symbols the same way the Python extractor turns
functions into symbols, so a `docs/decisions` + `docs/tickets` tree (this
repo's own, or any product's) diffs and renders exactly like a code tree:
a session proposes decisions, the human reviews them on the graph with
rationale attached, and the accepted result — a set of tickets, committed
by the human like any other change — becomes the input to the code-review
loop above. Two domains, one pipeline.

## Open product questions

- Granularity of a "node" for diff/rationale purposes: file, class, or function? (Function-level is the vision; file-level is the pragmatic v1 — see architecture notes.)
- Where does the developer type prompts: resolved — both a console `claude` invocation and the graph app's own prompt box work against the same session (ADR 011, ADR 058).
- Single-session tool first, or multi-agent (several Claude sessions staging changes into one graph)?
