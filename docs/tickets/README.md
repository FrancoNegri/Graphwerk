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
| [035](035-grouped-band-ordering.md) | Directory-grouped within-band ordering | done | [010](../decisions/010-directory-band-grouping.md) |
| [036](036-group-in-snapshot.md) | `GraphNode.group` in the snapshot payload | done | [010](../decisions/010-directory-band-grouping.md) |
| [037](037-group-tint-legend.md) | Directory tint + legend in the UI | done | [010](../decisions/010-directory-band-grouping.md) |
| [038](038-session-runner.md) | SessionRunner: spawn and track one headless agent session | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [039](039-prompt-endpoints.md) | `/api/prompt` + `/api/session` endpoints and the permissions flag | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [040](040-prompt-box-ui.md) | Prompt box + busy indicator in the UI | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [041](041-session-guidance-text.md) | Session guidance text + round-trip attribution test | done | [012](../decisions/012-rationale-session-guidance.md) |
| [042](042-session-runner-system-prompt.md) | `SessionRunner` gains a `system_prompt` parameter | done | [012](../decisions/012-rationale-session-guidance.md) |
| [043](043-wire-session-guidance-into-serve.md) | Wire `SESSION_GUIDANCE` into `cli._serve`'s `SessionRunner` | done | [012](../decisions/012-rationale-session-guidance.md) |
| [044](044-show-deps-calls-toggle.md) | "show deps + calls" edge visibility toggle | done | [013](../decisions/013-graph-edge-visibility-toggle.md) |
| [045](045-fix-polling-loop-overlap.md) | Fix unbounded overlap in the hash/session polling loop | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [046](046-split-imports-calls-toggle.md) | Split "show deps + calls" into independent imports/calls toggles | done | [014](../decisions/014-split-imports-calls-toggle.md) |
| [047](047-generalize-container-collapse.md) | Generalize collapse to every container, always collapsed by default | done | [015](../decisions/015-contract-by-default.md) |
| [048](048-show-calls-default-on.md) | `show-calls` defaults to on | done | [015](../decisions/015-contract-by-default.md) |
| [049](049-call-edge-status-model.md) | `GraphEdge.status` computed for `calls` edges | done | [016](../decisions/016-call-edge-status.md) |
| [050](050-color-call-edges-by-status.md) | Color `calls` edges by their status | done | [016](../decisions/016-call-edge-status.md) |
| [051](051-click-edge-lists-underlying-calls.md) | Clicking a `calls` edge lists the calls it collapsed | done | [016](../decisions/016-call-edge-status.md) |
| [052](052-edge-calls-show-code.md) | Edge-calls panel renders caller/callee code | done | [017](../decisions/017-edge-calls-show-code.md) |
| [053](053-taxi-edge-routing.md) | Orthogonal (taxi) routing for calls/imports edges | rejected | [018](../decisions/018-orthogonal-edge-routing.md) |
| [054](054-relative-import-level.md) | Relative imports resolve using their dot-level, not a bare module name | ready | [001](../decisions/001-phase-2-real-session.md) |
| [055](055-cache-file-index-by-fingerprint.md) | Cache parsed `FileIndex` per file by mtime/size fingerprint | done | [019](../decisions/019-snapshot-recompute-caching.md) |
| [056](056-cache-code-view-by-content.md) | Cache per-node code view by content identity | done | [019](../decisions/019-snapshot-recompute-caching.md) |
| [057](057-loadgraph-in-flight-guard.md) | Guard `loadGraph()` against overlapping in-flight calls | done | [011](../decisions/011-prompt-box-session-kickoff.md) |
| [058](058-wheel-zoom-feel.md) | Tune wheel-zoom sensitivity and bounds | done | [020](../decisions/020-edge-hover-reveal-and-zoom-feel.md) |
| [059](059-hover-reveal-unchanged-edges.md) | Hide unchanged-status edges by default; reveal on node hover | done | [020](../decisions/020-edge-hover-reveal-and-zoom-feel.md) |
| [060](060-skip-generic-wrapper-dir-grouping.md) | Skip generic wrapper directories in file grouping | done | [021](../decisions/021-src-layout-grouping.md) |
| [061](061-layer-from-entry-points.md) | Layer by longest path from entry points, not to leaves | done | [022](../decisions/022-entry-points-anchor-top-layer.md) |
| [062](062-render-layer-zero-at-top.md) | Render layer 0 at the top of the graph | done | [022](../decisions/022-entry-points-anchor-top-layer.md) |
| [063](063-import-adjacency-survives-noise-filtered-files.md) | Import adjacency survives noise-filtered intermediate files | done | [023](../decisions/023-import-adjacency-drops-noise-filtered-and-test-edges.md) |
| [064](064-exclude-test-file-edges-from-layering.md) | Exclude test-file edges from import layering | done | [023](../decisions/023-import-adjacency-drops-noise-filtered-and-test-edges.md) |
| [065](065-extract-nested-imports.md) | Collect imports from the whole file, skipping TYPE_CHECKING blocks | done | [024](../decisions/024-extract-nested-imports.md) |
| [066](066-parse-guidance-bullets.md) | Parse the guidance bullet format as the primary rationale source | done | [025](../decisions/025-rationale-mention-confidence.md) |
| [067](067-tighten-prose-mention-fallback.md) | Tighten the prose-mention fallback (qualified refs, backtick-quoting) | done | [025](../decisions/025-rationale-mention-confidence.md) |
| [068](068-rationale-confidence-flag.md) | Track and expose rationale confidence per node | done | [025](../decisions/025-rationale-mention-confidence.md) |
| [069](069-ui-low-confidence-why-marker.md) | UI marker for low-confidence rationale | done | [025](../decisions/025-rationale-mention-confidence.md) |
| [070](070-guidance-covers-deletions.md) | Extend SESSION_GUIDANCE to cover deleted files | done | [026](../decisions/026-rationale-for-deleted-files.md) |
| [071](071-deletion-shaped-bullet-fallback.md) | Recognize a deletion-shaped guidance bullet as a fallback | done | [026](../decisions/026-rationale-for-deleted-files.md) |
| [072](072-track-bash-deletions-as-edits.md) | Track Bash-performed file deletions as transcript edit events | done | [026](../decisions/026-rationale-for-deleted-files.md) |
| [073](073-guidance-why-vs-what-example.md) | Sharpen SESSION_GUIDANCE with a why-vs-what contrastive example | done | [027](../decisions/027-rationale-must-justify-not-describe.md) |
| [074](074-detect-descriptive-only-bullets.md) | Detect purely-descriptive guidance bullets | done | [027](../decisions/027-rationale-must-justify-not-describe.md) |
| [075](075-ui-descriptive-only-marker.md) | UI marker for describes-only rationale | done | [027](../decisions/027-rationale-must-justify-not-describe.md) |
| [076](076-edge-calls-collapsible-dropdowns.md) | Fuse each edge-calls pair into a collapsed dropdown | done | [028](../decisions/028-edge-calls-dropdowns-and-code-mode-toggle.md) |
| [077](077-code-display-mode-toggle.md) | Sidebar toggle: code + changes vs. changes only | done | [028](../decisions/028-edge-calls-dropdowns-and-code-mode-toggle.md) |
| [078](078-collapsed-deleted-pill-dashed-treatment.md) | Collapsed deleted-status pills keep the dashed/faded look (hue superseded by 030: red, not stone) | done | [029](../decisions/029-collapsed-deleted-pill-visual-treatment.md) |
| [079](079-modified-status-turns-green.md) | `modified` status turns green | done | [030](../decisions/030-status-palette-modified-green-deleted-red.md) |
| [080](080-decouple-prompt-error-color.md) | Decouple `#prompt-error` from the status palette | done | [030](../decisions/030-status-palette-modified-green-deleted-red.md) |
| [081](081-scope-call-edges-to-shared-tree.md) | Scope call-edge target resolution to the caller's tree | done | [032](../decisions/032-call-edge-resolution-scoped-to-shared-tree.md) |
| [082](082-diff-imports-by-module-name.md) | Diff imports as added/removed/unchanged per file | done | [033](../decisions/033-import-edge-status-and-pertinent-import-inspection.md) |
| [083](083-import-edges-carry-module-status.md) | Import edges carry per-module status and the responsible module name | done | [033](../decisions/033-import-edge-status-and-pertinent-import-inspection.md) |
| [084](084-import-edge-status-color-and-click-panel.md) | Import edges colored by status; clicking one lists the pertinent imports | done | [033](../decisions/033-import-edge-status-and-pertinent-import-inspection.md) |
| [085](085-scope-call-edges-to-caller-imports.md) | Scope call-edge resolution to the caller's file or its actual imports | done | [034](../decisions/034-call-edge-resolution-scoped-to-actual-imports.md) |
| [086](086-sessionrunner-settle-race.md) | Fix `SessionRunner._settle` race under concurrent status polls | done | [audit 001](../audit/runs/001-2026-07-17.md) |
| [087](087-normalize-bash-deletion-paths.md) | Normalize relative paths in Bash deletion tracking | done | [audit 001](../audit/runs/001-2026-07-17.md) |
| [088](088-record-shipped-deviations-adr-016-020.md) | Record shipped deviations in ADR 016/020 and tickets 049/058 | done | [audit 001](../audit/runs/001-2026-07-17.md) |
| [089](089-sync-ticket-statuses.md) | Sync ticket statuses with reality (README rows + tickets 078-080) | done | [audit 001](../audit/runs/001-2026-07-17.md) |
| [090](090-call-edges-carry-admitting-imports.md) | Call edges carry the imports that admit them | done | [035](../decisions/035-calls-panel-surfaces-admitting-imports.md) |
| [091](091-calls-panel-shows-admitting-imports.md) | Calls panel shows the imports admitting its calls | done | [035](../decisions/035-calls-panel-surfaces-admitting-imports.md) |
| [092](092-node-is-test-flag.md) | `GraphNode.is_test` in the snapshot payload | ready | [036](../decisions/036-hide-tests-exempts-changed-and-affected.md) |
| [093](093-hide-tests-exempts-changed-affected.md) | Hide-tests filter exempts changed and affected test nodes | ready | [036](../decisions/036-hide-tests-exempts-changed-and-affected.md) |
| [094](094-prompt-bar-docks-bottom.md) | Prompt bar docks to the bottom of the viewport | ready | [037](../decisions/037-bottom-session-bar-commit-discard.md) |
| [095](095-commit-message-guidance-and-parse.md) | Commit-message line: session guidance + transcript parse | ready | [037](../decisions/037-bottom-session-bar-commit-discard.md) |
| [096](096-commit-message-in-snapshot-meta.md) | Snapshot meta carries the mined commit message | ready | [037](../decisions/037-bottom-session-bar-commit-discard.md) |
| [097](097-commit-endpoint.md) | Commit-all: engine + `/api/commit` | ready | [037](../decisions/037-bottom-session-bar-commit-discard.md) |
| [098](098-discard-endpoint.md) | Discard-all: engine + `/api/discard` | ready | [037](../decisions/037-bottom-session-bar-commit-discard.md) |
| [099](099-session-bar-commit-discard-ui.md) | Session bar UI: commit message box + commit/discard buttons | ready | [037](../decisions/037-bottom-session-bar-commit-discard.md) |
| [100](100-extractor-captures-import-statement-text.md) | Extractor captures import statement text and line | ready | [038](../decisions/038-admitting-imports-render-as-real-statements.md) |
| [101](101-via-imports-entries-carry-statement-code.md) | `via_imports` entries carry the statement as code lines | ready | [038](../decisions/038-admitting-imports-render-as-real-statements.md) |
| [102](102-admitting-imports-render-with-rendercode.md) | Admitting-imports section renders the statement via `renderCode` | ready | [038](../decisions/038-admitting-imports-render-as-real-statements.md) |
