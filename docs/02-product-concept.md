# Product Concept: Graph-Based Staging & Review for AI Code Changes

## The idea

A developer tool that inverts how AI-generated code changes are reviewed.

1. The app starts, reads a codebase, and renders it as an interactive graph (files, classes, functions; import and call edges).
2. The developer runs Claude Code and asks for a feature as usual.
3. Claude generates changes — but instead of landing directly in the working tree, they land in a **staging layer** connected to the graph app.
4. The graph updates live: **modified symbols in green, new ones in blue, deleted in red** (ADR 030).
5. Each changed file/class carries a **"why" explanation** — the rationale for the change, captured from the agent — shown when the node is selected.
6. The developer reviews at their own pace, applying changes **node by node** as they see fit.
7. If a change looks wrong, the developer can reject that node with a comment, which **re-triggers just that part of the prompt** in the same Claude session.

The graph is the review surface. Today's review surface for AI changes is a flat text diff (terminal prompt, Cursor's review pane, a PR); this replaces it with a structural view that shows *where* in the architecture the change lands and *what it touches*.

## Prior-art check (July 2026): appears to be novel

Searched for existing tools in this space. Findings:

- The entire "code graph + AI" ecosystem points in the **opposite direction**: graphs are built *for the agent* (context efficiency), while the human still reviews text diffs. [code-review-graph](https://github.com/tirth8205/code-review-graph) is the closest by name and even does blast-radius analysis — but its graph feeds the AI reviewer, not the human.
- Whole-codebase explorers (Sourcetrail, Understand, Emerge) have no AI-agent integration at all.
- No tool found that (a) stages AI changes away from the working tree, (b) visualizes the staged delta on a symbol graph, and (c) offers selective, node-level apply.

**Symbol-level selective apply on a live graph is unclaimed territory.**

## What makes it more than a diff viewer

- **Structural context:** a diff shows text; the graph shows that the new `PaymentValidator` sits between `CheckoutService` and the gateway, and which callers are affected.
- **Blast radius for humans:** color affected-but-unchanged nodes (e.g., yellow = callers of a changed function) so the reviewer sees impact, not just edits.
- **Change-dependency edges:** the graph knows call edges, so it can draw dependencies *between staged changes* ("this new class is useless without the call-site change over there") and offer "apply group." No flat diff can express this. This is the killer feature — see [03-architecture-notes.md](03-architecture-notes.md).
- **Per-node rationale:** every changed node explains *why* it changed, in the agent's own words. This turns review from "is this code correct?" into the stronger check "does the stated intent match what the code actually does?" — and a rejection can attack the reasoning directly ("your stated reason doesn't hold because...").
- **Targeted re-prompting:** rejecting a node with a comment becomes a scoped follow-up in the same agent session, instead of re-running the whole prompt.

## Open product questions

- Granularity of a "node" for apply purposes: file, class, or function? (Function-level is the vision; file-level is the pragmatic v1 — see architecture notes.)
- Where does the developer type prompts: keep the terminal, or move prompting into the graph app?
- Single-session tool first, or multi-agent (several Claude sessions staging changes into one graph)?
