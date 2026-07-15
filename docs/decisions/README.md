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
