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
| [015](015-symbol-layered-placement.md) | Layered placement for symbols within an expanded file | ready | [003](../decisions/003-symbol-layered-placement.md) |
| [016](016-source-in-snapshot.md) | Thread full source text into the snapshot for every node | ready | [004](../decisions/004-always-show-source.md) |
| [017](017-sidebar-fallback-source.md) | Sidebar: render source as fallback code view when a node has no diff | ready | [004](../decisions/004-always-show-source.md) |
