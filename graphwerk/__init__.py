"""graphwerk — graph-based staging and review layer for AI-generated code changes.

Layers (see docs/03-architecture-notes.md):
  indexing/   symbols + edges from source (pure, stdlib ast)
  staging/    shadow workspace (git worktree) + tree-vs-tree symbol diff
  rationale/  "why" per change, mined from Claude Code transcripts or a sidecar file
  apply.py    apply staged changes to the base tree / reject with feedback
  service.py  orchestrates the above into graph snapshots
  server.py   FastAPI API + static UI
"""

__version__ = "0.1.0"
