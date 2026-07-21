# Graphwerk

A developer tool concept: a **graph-based review layer** over an AI coding agent (Claude Code) working in your own repo. The app reads a codebase, renders it as a graph, and as the agent edits files on disk the graph updates live — modified symbols in red, new ones in blue, each annotated with *why* it changed. The developer reviews at their own pace, lands changes with their own plain `git commit`, and can send targeted feedback to re-run just the parts that look wrong.

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
Click a node to read the diff and the *why*. The UI polls for changes, so
edits made on disk appear within ~1.5 s.

To review a real Claude Code session instead of the demo:

```bash
.venv/bin/python -m graphwerk start   # prints the `claude` invocation to run
                                       # in your repo, and serves the UI
```

`start` finds the session transcript automatically (no `--transcript` flag
needed) by matching the repo path to Claude Code's `~/.claude/projects/`
layout. For manual control:

```bash
.venv/bin/python -m graphwerk serve --repo . [--base-ref <ref>] \
    [--transcript ~/.claude/projects/<project>/<session>.jsonl]
```

## Layout

```
graphwerk/
  models.py       core domain model (Symbol, GraphNode, Status, Snapshot)
  indexing/       stdlib-ast symbol extraction + git-aware file walk (tree-sitter slot-in later)
  staging/        symbol-level diff between a base git ref and the working directory
  rationale/      "why" per change: sidecar JSON + auto-discovered Claude transcript mining
  service.py      snapshot assembly, blast-radius marking, state hash
  server.py       FastAPI API + static hosting
  cli.py          demo / serve / start entry points
static/           Cytoscape.js review UI (the only JS in the project): collapse/expand,
                  changed-only view, import-depth layered layout
```

## Status

Phase 2 — real session, end to end (July 2026): `graphwerk start` reviews an
actual Claude Code session with no manual transcript setup, and this loop has
been dogfooded (a graphwerk ticket was implemented and reviewed through the
UI — [ADR 001](docs/decisions/001-phase-2-real-session.md)). ADR 058 (also
July 2026) retired the shadow worktree and the apply/approval/commit/discard
engine: graphwerk no longer mutates files at all, and reviews the developer's
own working directory against a recorded base git ref. Landing or undoing a
change is the developer's own plain git operation. See
[docs/04-roadmap.md](docs/04-roadmap.md) for what's next (closing the reject
loop so feedback re-prompts the live session) and
[docs/decisions/](docs/decisions/README.md) for the ADRs and tickets in flight.
