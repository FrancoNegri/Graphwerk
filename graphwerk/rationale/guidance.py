"""Standing instruction given to spawned sessions (ADR 012).

Shapes the agent's closing narration into the shape ADR 006's mention-based
attribution already prefers: a distinct line per changed file naming its
path and symbols, so the miner has real per-file material to attribute
instead of falling back to generic process narration.
"""

from __future__ import annotations

SESSION_GUIDANCE = (
    "When you finish making the requested change, end your final message "
    "with a summary of the changes: one line per changed file, each naming "
    "the file's path and the key symbols you changed in it, and stating why "
    "that change serves the request (not what the code does). For example:\n"
    "- `path/to/file.py` (`SymbolName`): reason this change serves the request"
)
