# Graphwerk

A developer tool concept: a **graph-based staging and review layer** between an AI coding agent (Claude Code) and the filesystem. The app reads a codebase, renders it as a graph, and when the agent proposes changes they land in the graph first — modified symbols in red, new ones in blue, each annotated with *why* it changed — instead of on disk. The developer reviews and applies changes node by node, at their own pace, and can send targeted feedback to re-run just the parts that look wrong.

## Documents

- [docs/01-tool-landscape.md](docs/01-tool-landscape.md) — survey of existing code-graph visualization tools and Claude Code integrations
- [docs/02-product-concept.md](docs/02-product-concept.md) — the core idea, prior-art check, and why it appears to be novel
- [docs/03-architecture-notes.md](docs/03-architecture-notes.md) — design analysis: the write-interception trap, the shadow-workspace approach, hard problems, and a minimal prototype plan
- [docs/04-roadmap.md](docs/04-roadmap.md) — phased plan and current phase
- [docs/decisions/](docs/decisions/README.md) — ADRs behind nontrivial features; [docs/tickets/](docs/tickets/README.md) — the scoped units of work each ADR splits into

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install fastapi uvicorn   # once
.venv/bin/python -m graphwerk demo        # build scripted demo + open http://127.0.0.1:8135
```

The demo simulates the state after asking Claude to "add payment validation,
retries, and receipts to the shop app": modified symbols show red, new ones
blue, deleted ones grey (dashed), and unchanged callers of changed code amber.
Click a node to read the diff and the *why*, then **Apply** it into the base
tree or **Reject** it with a comment (shown as the re-prompt that a full build
would send back into the live Claude session). The UI polls for changes, so
edits to either tree appear within ~1.5 s.

To review a real Claude Code session instead of the demo:

```bash
.venv/bin/python -m graphwerk start   # creates a shadow worktree, prints the
                                       # `claude` invocation to run inside it,
                                       # and serves the UI
```

`start` finds the session transcript automatically (no `--transcript` flag
needed) by matching the worktree path to Claude Code's `~/.claude/projects/`
layout. For manual control over the two trees:

```bash
.venv/bin/python -m graphwerk serve --base . --staged ../myrepo-staging \
    [--transcript ~/.claude/projects/<project>/<session>.jsonl]
```

## Layout

```
graphwerk/
  models.py       core domain model (Symbol, GraphNode, Status, Snapshot)
  indexing/       stdlib-ast symbol extraction + git-aware file walk (tree-sitter slot-in later)
  staging/        shadow workspace (git worktree) + symbol-level tree diff
  rationale/      "why" per change: sidecar JSON + auto-discovered Claude transcript mining
  apply.py        file-level apply / reject-with-feedback
  service.py      snapshot assembly, blast-radius marking, state hash
  server.py       FastAPI API + static hosting
  cli.py          demo / serve / start entry points
static/           Cytoscape.js review UI (the only JS in the project): collapse/expand,
                  changed-only view, import-depth layered layout
```

## Status

Phase 2 — real session, end to end (July 2026): `graphwerk start` reviews an
actual Claude Code session with no manual worktree/transcript setup, and this
loop has been dogfooded (a graphwerk ticket was implemented in the staging
worktree and reviewed/applied through the UI — [ADR 001](docs/decisions/001-phase-2-real-session.md)).
Apply/reject are still file-level; reject records the re-prompt instead of
driving a live session. See [docs/04-roadmap.md](docs/04-roadmap.md) for what's
next (closing the reject loop, symbol-level apply) and
[docs/decisions/](docs/decisions/README.md) for the ADRs and tickets in flight.
