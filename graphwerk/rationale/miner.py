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
from dataclasses import dataclass
from pathlib import Path

from graphwerk.rationale.attribution import (
    MAX_WHY_LEN,
    attribute_files,
    attribute_guidance_bullets,
    attribute_symbols,
    reason_justifies,
)
from graphwerk.rationale.discovery import find_latest_transcript
from graphwerk.rationale.transcript import parse_transcript


@dataclass(frozen=True)
class RationaleEntry:
    """One transcript-mined rationale, tagged with how it was found — a
    guidance bullet or explicit prose mention names the file/symbol
    directly (confident); the proximity fallback is just the nearest
    preceding narration, possibly about something else entirely.

    ``justifies`` (ADR 027) is only meaningful when ``confident`` is True —
    it's None for the proximity fallback, where content-quality flagging
    doesn't apply on top of the existing low-confidence marker."""

    text: str
    confident: bool
    justifies: bool | None = None


@dataclass
class RationaleStatus:
    """What the last reload() actually found — paths are None unless the
    source was really loaded, so "no rationale" stays diagnosable."""

    sidecar_path: str | None = None
    sidecar_entries: int = 0
    transcript_path: str | None = None
    transcript_entries: int = 0
    warning: str | None = None

    def to_dict(self) -> dict:
        return {
            "sidecar_path": self.sidecar_path,
            "sidecar_entries": self.sidecar_entries,
            "transcript_path": self.transcript_path,
            "transcript_entries": self.transcript_entries,
            "warning": self.warning,
        }


class RationaleStore:
    def __init__(self, sidecar_path: Path | None = None, transcript_path: Path | None = None,
                 staged_root: Path | None = None, base_root: Path | None = None):
        self.sidecar_path = sidecar_path
        self.transcript_path = transcript_path
        self.staged_root = staged_root
        self.base_root = base_root
        self._sidecar: dict[str, str] = {}
        self._transcript: dict[str, RationaleEntry] = {}  # rel_path -> latest narration
        self.status = RationaleStatus()
        self.reload()

    def reload(self, changed_symbols: dict[str, list[str]] | None = None) -> None:
        sidecar_entries = self._load_sidecar()
        self._sidecar = sidecar_entries if sidecar_entries is not None else {}
        transcript_path = self._usable_transcript_path()
        self._transcript = self._mine_transcript(transcript_path, changed_symbols or {})
        self.status = RationaleStatus(
            sidecar_path=str(self.sidecar_path) if sidecar_entries is not None else None,
            sidecar_entries=len(self._sidecar),
            transcript_path=str(transcript_path) if transcript_path else None,
            transcript_entries=len(self._transcript),
            warning=None if transcript_path else self._misplaced_session_warning(),
        )

    def _misplaced_session_warning(self) -> str | None:
        """The observed dogfood failure: the agent session ran in the base tree,
        so its transcript sits with the base root's project dir. That transcript
        is never adopted as a rationale source (ADR 009) — it only powers this
        warning."""
        if not self.base_root:
            return None
        base_transcript = find_latest_transcript(self.base_root)
        if not base_transcript:
            return None
        _, edits = parse_transcript(base_transcript, self.base_root)
        if not edits:
            return None
        return (
            f"The latest agent session edited the base tree ({self.base_root}), "
            f"not the staging worktree — run the agent in the staging worktree, "
            f"or check whether --base and --staged are swapped."
        )

    def _usable_transcript_path(self) -> Path | None:
        path = self._resolve_transcript_path()
        if path and path.exists() and self.staged_root:
            return path
        return None

    def _resolve_transcript_path(self) -> Path | None:
        if self.transcript_path:
            return self.transcript_path
        if self.staged_root:
            return find_latest_transcript(self.staged_root)
        return None

    def status_message(self, changed_nodes_exist: bool) -> str | None:
        """One reviewer-facing line about rationale health; None when all is well."""
        if self.status.warning:
            return self.status.warning
        no_source = self.status.sidecar_entries == 0 and self.status.transcript_entries == 0
        if changed_nodes_exist and no_source:
            return f"No rationale source found for {self.staged_root}."
        return None

    def why_for(self, rel_path: str, qualname: str | None = None) -> str | None:
        """Most specific rationale available for a node; sidecar beats transcript."""
        keys = self._lookup_keys(rel_path, qualname)
        for key in keys:
            if self._sidecar.get(key):
                return self._sidecar[key]
        for key in keys:
            entry = self._transcript.get(key)
            if entry:
                return entry.text
        return None

    def justifies_for(self, rel_path: str, qualname: str | None = None) -> bool | None:
        """Whether the rationale text argues for the change rather than
        merely describing the code (ADR 027) — None when there's no
        confident why to evaluate (no source at all, or the proximity
        fallback, which is already flagged low-confidence for a different
        reason)."""
        keys = self._lookup_keys(rel_path, qualname)
        for key in keys:
            if self._sidecar.get(key):
                return reason_justifies(self._sidecar[key])
        for key in keys:
            entry = self._transcript.get(key)
            if entry:
                return entry.justifies
        return None

    def confident_for(self, rel_path: str, qualname: str | None = None) -> bool:
        """Whether the text why_for returns came from an explicit source
        (sidecar, a guidance bullet, or a prose mention) rather than the
        proximity fallback (nearest preceding narration, possibly about a
        different file entirely)."""
        keys = self._lookup_keys(rel_path, qualname)
        for key in keys:
            if self._sidecar.get(key):
                return True
        for key in keys:
            entry = self._transcript.get(key)
            if entry:
                return entry.confident
        return True

    @staticmethod
    def _lookup_keys(rel_path: str, qualname: str | None) -> list[str]:
        return [f"{rel_path}::{qualname}", rel_path] if qualname else [rel_path]

    def _load_sidecar(self) -> dict[str, str] | None:
        """None when there is no usable sidecar (missing/unreadable), so the
        status can tell that apart from a sidecar that loaded zero entries."""
        if not self.sidecar_path or not self.sidecar_path.exists():
            return None
        try:
            data = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
            return {str(k): str(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError):
            return None

    def _mine_transcript(self, transcript_path: Path | None,
                         changed_symbols: dict[str, list[str]]) -> dict[str, RationaleEntry]:
        if not transcript_path:
            return {}
        segments, edits = parse_transcript(transcript_path, self.staged_root)
        rationale: dict[str, RationaleEntry] = {}
        for edit in edits:
            if edit.last_segment_index is not None:
                text = segments[edit.last_segment_index].text[:MAX_WHY_LEN]
                rationale[edit.rel_path] = RationaleEntry(text=text, confident=False)
        for key, text in attribute_files(segments, sorted({edit.rel_path for edit in edits})).items():
            rationale[key] = RationaleEntry(text=text, confident=True, justifies=reason_justifies(text))
        for key, text in attribute_symbols(segments, changed_symbols).items():
            rationale[key] = RationaleEntry(text=text, confident=True, justifies=reason_justifies(text))
        # Highest priority (ADR 025): a dedicated guidance bullet always wins,
        # even over a later prose segment that merely repeats the filename.
        for key, text in attribute_guidance_bullets(segments, changed_symbols).items():
            rationale[key] = RationaleEntry(text=text, confident=True, justifies=reason_justifies(text))
        return rationale
