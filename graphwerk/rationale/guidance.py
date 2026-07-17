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
    "- `path/to/file.py` (`SymbolName`): reason this change serves the request\n"
    "\n"
    "That reason has to justify the change, not just describe the code — "
    "the same fact stated two ways reads very differently to a reviewer. "
    "For example, for the same hypothetical file:\n"
    "- describes only (not enough): `path/to/file.py` (`SymbolName`): "
    "validates the payload and writes it to the database\n"
    "- justifies (what's asked for): `path/to/file.py` (`SymbolName`): "
    "validation moved here so it runs before the retry loop added below\n"
    "\n"
    "If you delete a file, give it a line in the same shape, with `removed` "
    "as the reason's lead word:\n"
    "- `path/to/old_file.py`: removed — reason\n"
    "\n"
    "After the per-file lines, close your final message with exactly one "
    "line of this form:\n"
    "Commit-message: <concise one-line summary of the whole change set>"
)
