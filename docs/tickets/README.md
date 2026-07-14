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
| [007](007-dogfood-run.md) | Dogfood: review a real graphwerk change with graphwerk | ready | [001](../decisions/001-phase-2-real-session.md) |
