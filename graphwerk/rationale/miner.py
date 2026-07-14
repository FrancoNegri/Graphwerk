"""The "why" behind each change.

Two sources, merged (sidecar wins on conflicts):

1. Sidecar JSON — ``{"<rel_path>": "...", "<rel_path>::<qualname>": "..."}``.
   Written by the demo scenario; later, a post-hoc summarization pass.
2. Claude Code session transcript (JSONL) — the assistant narration immediately
   preceding an Edit/Write tool call is, in practice, the rationale for that
   edit. Mining it costs zero prompt overhead.
"""

from __future__ import annotations

import json
from pathlib import Path

from graphwerk.rationale.discovery import find_latest_transcript

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MAX_WHY_LEN = 700


class RationaleStore:
    def __init__(self, sidecar_path: Path | None = None, transcript_path: Path | None = None,
                 staged_root: Path | None = None):
        self.sidecar_path = sidecar_path
        self.transcript_path = transcript_path
        self.staged_root = staged_root
        self._sidecar: dict[str, str] = {}
        self._transcript: dict[str, str] = {}  # rel_path -> latest narration
        self.reload()

    def reload(self) -> None:
        self._sidecar = self._load_sidecar()
        self._transcript = self._mine_transcript(self._resolve_transcript_path())

    def _resolve_transcript_path(self) -> Path | None:
        if self.transcript_path:
            return self.transcript_path
        if self.staged_root:
            return find_latest_transcript(self.staged_root)
        return None

    def why_for(self, rel_path: str, qualname: str | None = None) -> str | None:
        """Most specific rationale available for a node."""
        if qualname:
            specific = self._sidecar.get(f"{rel_path}::{qualname}")
            if specific:
                return specific
        return self._sidecar.get(rel_path) or self._transcript.get(rel_path)

    def _load_sidecar(self) -> dict[str, str]:
        if not self.sidecar_path or not self.sidecar_path.exists():
            return {}
        try:
            data = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
            return {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _mine_transcript(self, transcript_path: Path | None) -> dict[str, str]:
        if not transcript_path or not transcript_path.exists() or not self.staged_root:
            return {}
        rationale: dict[str, str] = {}
        last_text = ""
        try:
            lines = transcript_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return {}
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text", "").strip():
                    last_text = block["text"].strip()
                elif block.get("type") == "tool_use" and block.get("name") in EDIT_TOOLS:
                    file_path = (block.get("input") or {}).get("file_path")
                    if file_path and last_text:
                        rel = self._to_rel(file_path)
                        if rel:
                            rationale[rel] = last_text[:MAX_WHY_LEN]
        return rationale

    def _to_rel(self, file_path: str) -> str | None:
        try:
            return Path(file_path).resolve().relative_to(self.staged_root.resolve()).as_posix()
        except ValueError:
            return None
