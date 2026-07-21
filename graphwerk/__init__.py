"""graphwerk — graph-based staging and review layer for AI-generated code changes.

Layers (see docs/03-architecture-notes.md):
  indexing/   symbols + edges from source (pure, stdlib ast)
  staging/    symbol diff between the working directory and a base git ref
  rationale/  "why" per change, mined from Claude Code transcripts or a sidecar file
  service.py  orchestrates the above into graph snapshots
  server.py   FastAPI API + static UI
"""

__version__ = "0.2.0"
