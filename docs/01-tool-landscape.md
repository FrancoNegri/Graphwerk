# Tool Landscape: Graph-Based Code Visualization (July 2026)

Survey of existing tools, grouped by what they actually do. The key finding: the ecosystem splits into *graphs for humans* (classic explorers, no AI integration) and *graphs for AI agents* (MCP servers, mostly no human-facing UI). Almost nothing bridges both, and nothing uses a graph as a **review surface for AI-proposed changes** (see [02-product-concept.md](02-product-concept.md)).

## 1. Whole-codebase explorers (interactive graph UIs, human-facing)

None of these integrate with Claude Code.

- **Sourcetrail** — the best-known open-source explorer. Indexes C/C++/Java/Python into an interactive graph of classes, functions, call/include relationships. Original project discontinued in 2021; community forks keep it alive.
- **Understand (SciTools)** — commercial, mature. Call graphs, dependency graphs, UML-ish views, many languages.
- **CodeScene** — commercial. Hotspot and change-coupling graphs derived from git history + static analysis.
- **Emerge** — open source. Scans a codebase and emits interactive d3-based dependency graphs for several languages.
- **CodeCharta** — 3D "code city" maps from metrics; structure overviews rather than true graphs.

## 2. Dependency / call-graph generators (CLI, usually Graphviz/DOT or JSON output)

- **madge** — JS/TS module dependency graphs, circular-dependency detection.
- **pydeps** / **pyan** — Python import graphs and call graphs.
- **code2flow** — call graphs for Python, JS, Ruby, PHP.
- **dep-tree** — dependency trees with a 3D entropy view.
- **Doxygen + Graphviz** — classic route for C/C++ call and include graphs.
- Ecosystem-native options: `go mod graph` / `goda` (Go), `jdeps` (Java), etc.

## 3. Editor-integrated

- **Crabviz** (VS Code) — interactive call graphs via LSP, so it works for any language with a language server.
- **IntelliJ dependency diagrams**, **Visual Studio Code Maps** — built-in graph views.

## 4. Code-graph MCP servers for Claude Code (graphs for the *agent*)

A category that emerged around 2025–2026. Primary purpose: give the agent a queryable knowledge graph so it stops re-reading files (large token/tool-call reductions). Most have **no human-facing visualization**.

- **[codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)** — the closest thing to a "whole-codebase explorer that works with Claude Code natively." Verified against its repo:
  - Indexes the entire codebase (functions, classes, imports, call chains, HTTP routes, Dockerfiles/K8s manifests) into a persistent SQLite knowledge graph.
  - 158 languages via vendored tree-sitter grammars; hybrid LSP semantic type resolution for 12 languages.
  - Optional **3D graph explorer UI at `localhost:9749`** (the `ui` variant / `--ui` flag).
  - Claude-Code-specific installer: writes the MCP entry to `~/.claude/.mcp.json`, installs 4 discovery skills, and adds a PreToolUse hook that augments Grep/Glob results with graph data.
- **[colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)** — local tree-sitter + SQLite + FTS5 knowledge graph; claims ~35% API cost and ~70% tool-call reduction. Supports Claude Code, Cursor, Codex, and others. No review UI.
- **[sdsrss/code-graph-mcp](https://github.com/sdsrss/code-graph-mcp)** — AST knowledge graph with semantic search, call-graph traversal, HTTP route tracing, impact analysis; 10 languages.
- **[Graphify](https://dev.to/mir_mursalin_ankur/graphify-code-review-graph-build-a-self-updating-knowledge-graph-for-claude-code-and-other-ai-j1m)** — self-updating import/call/dependency graph, 25+ languages.
- **[code-review-graph](https://github.com/tirth8205/code-review-graph)** — local-first code intelligence graph for MCP/CLI. Signature feature is **blast-radius analysis**: when a file changes, the graph traces every caller, dependent, and test that could be affected, so the AI reviews only relevant files. Has HTML/GraphML/SVG graph export. Note the direction: the graph helps the *AI* review; the human still reads text diffs.
- **[CodeLayers](https://codelayers.ai/blog/complete-guide-code-visualization-2026)** — commercial; human-facing codebase map plus 14 MCP tools for the agent. (Source is their own marketing blog — weigh accordingly.)

## 5. Generate-the-visualization approaches

- [Popular prompt gist](https://gist.github.com/aessam/963beecba29660a532b11f03b27e1b92) that has Claude Code emit a multi-level interactive D3.js dependency graph (system / module / full views) for any repo. One-shot artifact, not a live indexed explorer.

## Common building blocks (relevant for building our own)

- **Parsing/symbols:** tree-sitter (broad language coverage) or LSP (accurate cross-file resolution).
- **Rendering:** Cytoscape.js (compound nodes — files containing symbols — natively supported; usually the sweet spot), d3-force, or Graphviz.
- **Agent control:** Claude Agent SDK (persistent, steerable sessions), Claude Code hooks (PreToolUse can intercept/deny tool calls), MCP servers, git worktrees (first-class in Claude Code).
