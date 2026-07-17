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
| [020](020-edge-hover-reveal-and-zoom-feel.md) | Hide unchanged edges behind hover reveal; tune wheel-zoom feel | proposed |
| [021](021-src-layout-grouping.md) | Skip generic wrapper directories when grouping files by top-level directory | proposed |
| [022](022-entry-points-anchor-top-layer.md) | Layer from entry points downward, not from leaves upward | proposed |
| [023](023-import-adjacency-drops-noise-filtered-and-test-edges.md) | Import adjacency must survive noise-filtered nodes and ignore test-sourced edges | proposed |
| [024](024-extract-nested-imports.md) | Extract imports from the whole file, not just the top level | proposed |
| [025](025-rationale-mention-confidence.md) | Rationale attribution: prefer the guidance bullet format, tighten the prose fallback, mark confidence | proposed |
| [026](026-rationale-for-deleted-files.md) | Rationale for deleted files | proposed |
| [027](027-rationale-must-justify-not-describe.md) | Rationale bullets must justify, not just describe | proposed |
| [028](028-edge-calls-dropdowns-and-code-mode-toggle.md) | Collapsible per-call dropdowns; a sidebar toggle for code+changes vs. changes-only | proposed |
| [029](029-collapsed-deleted-pill-visual-treatment.md) | Collapsed deleted-status containers keep the faded/dashed treatment | proposed (hue superseded by 030) |
| [030](030-status-palette-modified-green-deleted-red.md) | Status palette: `modified` turns green, `deleted` turns red | proposed |
| [031](031-modified-status-blue-not-green.md) | `modified` status turns blue, not green | rejected |
