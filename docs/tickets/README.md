# Tickets

Small, independently implementable units of work, each traceable to an ADR
in `docs/decisions/`. Written by the `north-star` skill, implemented one at a
time by the `ticket` skill via TDD.

A ticket should be small enough to implement in one sitting: one or two
files touched, one clear acceptance criterion set, no bundled unrelated
changes.

Numbered sequentially, independent of `docs/decisions/`.

| # | Title | Status | Decision |
|---|-------|--------|----------|
| [001](001-transcript-discovery.md) | Transcript auto-discovery function | done | [001](../decisions/001-phase-2-real-session.md) |
| [002](002-rationale-auto-discovery.md) | RationaleStore uses auto-discovered transcripts | done | [001](../decisions/001-phase-2-real-session.md) |
| [003](003-git-aware-walk.md) | Git-aware file enumeration (.gitignore + symlinks) | done | [001](../decisions/001-phase-2-real-session.md) |
| [004](004-start-command.md) | `graphwerk start` command | done | [001](../decisions/001-phase-2-real-session.md) |
| [005](005-collapse-expand.md) | Collapse/expand file nodes (double-click) | done | [001](../decisions/001-phase-2-real-session.md) |
| [006](006-changed-only-toggle.md) | "Changed + blast radius only" view toggle | done | [001](../decisions/001-phase-2-real-session.md) |
| [007](007-dogfood-run.md) | Dogfood: review a real graphwerk change with graphwerk | done | [001](../decisions/001-phase-2-real-session.md) |
| [008](008-unparseable-staged-file.md) | Distinct state for unparseable staged files | ready | [001](../decisions/001-phase-2-real-session.md) |
| [009](009-non-python-changes-visible.md) | Non-Python staged changes visible in the graph | ready | [001](../decisions/001-phase-2-real-session.md) |
| [010](010-collapse-by-default.md) | Collapse unchanged files by default | done | [002](../decisions/002-graph-layout-legibility.md) |
| [011](011-import-layer-assignment.md) | Import-depth layer assignment | done | [002](../decisions/002-graph-layout-legibility.md) |
| [012](012-layered-band-placement.md) | Layered band placement | done | [002](../decisions/002-graph-layout-legibility.md) |
| [013](013-src-layout-import-edges.md) | Import edges resolve src-layout and package roots | done | [001](../decisions/001-phase-2-real-session.md) |
| [014](014-symbol-layer-assignment.md) | Call-depth layer assignment for symbols within a file | done | [003](../decisions/003-symbol-layered-placement.md) |
| [015](015-symbol-layered-placement.md) | Layered placement for symbols within an expanded file | done | [003](../decisions/003-symbol-layered-placement.md) |
| [016](016-source-in-snapshot.md) | Thread full source text into the snapshot for every node | done | [004](../decisions/004-always-show-source.md) |
| [017](017-sidebar-fallback-source.md) | Sidebar: render source as fallback code view when a node has no diff | done | [004](../decisions/004-always-show-source.md) |
| [018](018-transcript-segmentation.md) | Transcript parser: ordered segments + edit events | done | [006](../decisions/006-rationale-mining-v2.md) |
| [019](019-file-mention-attribution.md) | File-level mention attribution | done | [006](../decisions/006-rationale-mining-v2.md) |
| [020](020-rationale-store-rewire.md) | RationaleStore mines via parser + attribution | done | [006](../decisions/006-rationale-mining-v2.md) |
| [021](021-symbol-mention-attribution.md) | Symbol-level mention attribution | done | [006](../decisions/006-rationale-mining-v2.md) |
| [022](022-token-highlighting.md) | Python token highlighting via stdlib tokenize | done | [007](../decisions/007-sidebar-code-view.md) |
| [023](023-merged-line-view.md) | Merged line view of base vs staged text | done | [007](../decisions/007-sidebar-code-view.md) |
| [024](024-code-view-builder.md) | Code view builder: merged lines + highlight spans | done | [007](../decisions/007-sidebar-code-view.md) |
| [025](025-filechange-both-texts.md) | FileChange carries base and staged full text | done | [007](../decisions/007-sidebar-code-view.md) |
| [026](026-snapshot-code-view.md) | Snapshot attaches a code view to every node | done | [007](../decisions/007-sidebar-code-view.md) |
| [027](027-sidebar-code-render.md) | Sidebar renders the unified code view | done | [007](../decisions/007-sidebar-code-view.md) |
| [028](028-drop-source-payload.md) | Drop the redundant source field from the node payload | done | [007](../decisions/007-sidebar-code-view.md) |
| [029](029-barycenter-ordering.md) | Within-layer ordering utility (barycenter sweeps) | done | [008](../decisions/008-within-layer-ordering.md) |
| [030](030-order-in-snapshot.md) | `GraphNode.order` in the snapshot payload | done | [008](../decisions/008-within-layer-ordering.md) |
| [031](031-band-anchor-sort.md) | Bands chain anchors in payload order | done | [008](../decisions/008-within-layer-ordering.md) |
| [032](032-rationale-source-meta.md) | Snapshot meta reports rationale sources | done | [009](../decisions/009-rationale-fails-loudly.md) |
| [033](033-misplaced-session-hint.md) | Misplaced-session hint when the transcript sits with the base tree | done | [009](../decisions/009-rationale-fails-loudly.md) |
| [034](034-rationale-status-banner.md) | UI banner for rationale source status | done | [009](../decisions/009-rationale-fails-loudly.md) |
| [035](035-grouped-band-ordering.md) | Directory-grouped within-band ordering | ready | [010](../decisions/010-directory-band-grouping.md) |
| [036](036-group-in-snapshot.md) | `GraphNode.group` in the snapshot payload | ready | [010](../decisions/010-directory-band-grouping.md) |
| [037](037-group-tint-legend.md) | Directory tint + legend in the UI | ready | [010](../decisions/010-directory-band-grouping.md) |
| [038](038-session-runner.md) | SessionRunner: spawn and track one headless agent session | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [039](039-prompt-endpoints.md) | `/api/prompt` + `/api/session` endpoints and the permissions flag | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [040](040-prompt-box-ui.md) | Prompt box + busy indicator in the UI | ready | [011](../decisions/011-prompt-box-session-kickoff.md) |
