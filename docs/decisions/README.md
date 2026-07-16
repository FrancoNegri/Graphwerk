# Decisions

Architecture Decision Records (ADRs) for graphwerk. Each file is one decision:
what problem it solves, what was chosen, what alternatives were rejected and
why, and what it costs. Written by the `north-star` skill before any
nontrivial feature is broken into tickets.

Numbered sequentially, independent of the topic docs in `docs/` (01-04).

| # | Title | Status |
|---|-------|--------|
| [001](001-phase-2-real-session.md) | Phase 2 — review a real Claude session end to end | proposed |
| [002](002-graph-layout-legibility.md) | Graph layout legibility: collapse-by-default + import-depth layers | proposed |
| [003](003-symbol-layered-placement.md) | Symbol-level layered placement within an expanded file | proposed |
| [004](004-always-show-source.md) | Show source for any selected node, not just diffs | proposed |
| [005](005-server-side-layers.md) | Layer computation moves server-side; the JS layer stays thin | accepted |
| [006](006-rationale-mining-v2.md) | Rationale mining v2: whole-transcript mention attribution | proposed |
| [007](007-sidebar-code-view.md) | Sidebar code view: full source with diff overlay and syntax highlighting | proposed |
| [008](008-within-layer-ordering.md) | Within-layer ordering: barycenter sweeps to shorten cross-layer edges | proposed |
| [009](009-rationale-fails-loudly.md) | Rationale fails loudly: source status in the payload + misplaced-session hint | proposed |
| [010](010-directory-band-grouping.md) | Directory-aware band grouping: files cluster by top-level directory within layers | proposed |
| [011](011-prompt-box-session-kickoff.md) | Prompt box: graphwerk kicks off the agent session (headless CLI subprocess) | proposed |
| [012](012-rationale-session-guidance.md) | Rationale guidance injected into spawned sessions | proposed |
| [013](013-graph-edge-visibility-toggle.md) | Import/call edges hidden by default behind a toggle | proposed |
| [014](014-split-imports-calls-toggle.md) | Split the combined edge toggle into independent imports/calls checkboxes | proposed |
| [015](015-contract-by-default.md) | Contract every container by default; show calls out of the box | proposed |
| [016](016-call-edge-status.md) | Color call edges by status; list what a collapsed edge represents | proposed |
| [017](017-edge-calls-show-code.md) | Clicking a calls edge shows caller/callee code, not just labels | proposed |
| [018](018-orthogonal-edge-routing.md) | Orthogonal (taxi) edge routing; defer bespoke hub treatment until judged with directory grouping | rejected |
| [019](019-snapshot-recompute-caching.md) | Cache repeated snapshot recomputation (indexing + code view) | accepted |
