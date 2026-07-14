# 009. Non-Python staged changes must be visible in the graph

Status: ready
Decision: docs/decisions/001-phase-2-real-session.md (dogfood finding, ticket 007)

## Goal

Every staged change is reviewable. In the ticket 007 dogfood run the agent
modified `pyproject.toml`; the graph never showed it, yet `/api/apply`
happily applied it. A reviewer can currently ship — or silently miss —
changes they were never shown. This is a review-surface hole, not a
language-support gap: full symbol indexing for other languages stays
Phase 5.

## Acceptance criteria

- The snapshot includes a file-level node (no symbol children, no edges)
  for every non-Python file that differs between base and staged —
  added, modified, or deleted — using the same git-aware enumeration as
  the Python walk.
- Node states and file-level apply/reject work on these nodes exactly as
  they do for Python file nodes.
- `state_hash` covers them, so the UI refreshes when only a non-Python
  file changes.
- Binary files get the node and a size/`(binary)` marker rather than a text
  diff.

## Likely files

- `graphwerk/indexing/walk.py` — enumerate all changed files, not only `.py`
- `graphwerk/staging/differ.py` — emit file-level nodes for them
- `graphwerk/service.py` — include them in snapshot + hash

## Out of scope

Symbol extraction for other languages (Phase 5, tree-sitter); rendering
text diffs for non-Python files in the detail panel beyond what the file
node already carries.
