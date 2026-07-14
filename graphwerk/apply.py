"""Apply staged changes to the base tree, or reject them with feedback.

v1 applies at file granularity: copy the staged file over the base file (or
delete the base file if the staged one is gone). Hunk-level apply is phase 2.

Reject produces the re-prompt payload that a full build would send back into
the live Claude session (Agent SDK / --resume); v1 records it and returns it
so the UI can show exactly what would be sent.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path


class ApplyEngine:
    def __init__(self, base_root: Path, staged_root: Path):
        self.base_root = base_root
        self.staged_root = staged_root
        self.feedback_log = base_root / ".graphwerk" / "feedback.jsonl"

    def apply_file(self, rel_path: str) -> str:
        src = self.staged_root / rel_path
        dst = self.base_root / rel_path
        if not _is_within(self.staged_root, src) or not _is_within(self.base_root, dst):
            raise ValueError(f"path escapes workspace: {rel_path}")
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return f"applied {rel_path}"
        if dst.exists():
            dst.unlink()
            return f"deleted {rel_path}"
        raise FileNotFoundError(rel_path)

    def reject(self, node_id: str, label: str, status: str, comment: str, diff: str) -> str:
        prompt = (
            f"The reviewer rejected the staged change to `{label}` ({status}) in {node_id.split('::')[0]}.\n"
            f"Reviewer comment: {comment}\n\n"
            f"The staged change was:\n{diff or '(no diff available)'}\n"
            f"Please redo just this part, keeping the rest of the change set intact."
        )
        self.feedback_log.parent.mkdir(parents=True, exist_ok=True)
        with self.feedback_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), "node": node_id, "comment": comment,
                                 "prompt": prompt}) + "\n")
        return prompt


def _is_within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
