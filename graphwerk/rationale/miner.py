"""The "why" behind each change.

Two sources, merged (sidecar wins on conflicts):

1. Sidecar JSON — ``{"<rel_path>": "...", "<rel_path>::<qualname>": "..."}``.
   Written by the demo scenario; later, a post-hoc summarization pass.
2. Claude Code session transcript (JSONL) — mention-based attribution over
   the whole session (ADR 006): the latest segment naming a file is its
   rationale, falling back to the narration preceding its edit. Mining it
   costs zero prompt overhead.
"""

from __future__ import annotations

import json
from pathlib import Path

from graphwerk.rationale.attribution import MAX_WHY_LEN, attribute_files, attribute_symbols
from graphwerk.rationale.discovery import find_latest_transcript
from graphwerk.rationale.transcript import parse_transcript


class RationaleStore:
    def __init__(self, sidecar_path: Path | None = None, transcript_path: Path | None = None,
                 staged_root: Path | None = None):
        self.sidecar_path = sidecar_path
        self.transcript_path = transcript_path
        self.staged_root = staged_root
        self._sidecar: dict[str, str] = {}
        self._transcript: dict[str, str] = {}  # rel_path -> latest narration
        self.reload()

    def reload(self, changed_symbols: dict[str, list[str]] | None = None) -> None:
        self._sidecar = self._load_sidecar()
        self._transcript = self._mine_transcript(self._resolve_transcript_path(),
                                                 changed_symbols or {})

    def _resolve_transcript_path(self) -> Path | None:
        if self.transcript_path:
            return self.transcript_path
        if self.staged_root:
            return find_latest_transcript(self.staged_root)
        return None

    def why_for(self, rel_path: str, qualname: str | None = None) -> str | None:
        """Most specific rationale available for a node; sidecar beats transcript."""
        keys = [f"{rel_path}::{qualname}", rel_path] if qualname else [rel_path]
        for source in (self._sidecar, self._transcript):
            for key in keys:
                if source.get(key):
                    return source[key]
        return None

    def _load_sidecar(self) -> dict[str, str]:
        if not self.sidecar_path or not self.sidecar_path.exists():
            return {}
        try:
            data = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
            return {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def _mine_transcript(self, transcript_path: Path | None,
                         changed_symbols: dict[str, list[str]]) -> dict[str, str]:
        if not transcript_path or not transcript_path.exists() or not self.staged_root:
            return {}
        segments, edits = parse_transcript(transcript_path, self.staged_root)
        rationale: dict[str, str] = {}
        for edit in edits:
            if edit.last_segment_index is not None:
                rationale[edit.rel_path] = segments[edit.last_segment_index].text[:MAX_WHY_LEN]
        rationale.update(attribute_files(segments, sorted({edit.rel_path for edit in edits})))
        rationale.update(attribute_symbols(segments, changed_symbols))
        return rationale
