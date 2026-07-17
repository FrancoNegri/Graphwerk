"""Pure parser: session transcript (JSONL) -> ordered segments + edit events.

Feeds mention-based attribution (ADR 006): segments are the units a file or
symbol mention is searched in, edit events anchor each touched file to its
place in the narration order.
"""

from __future__ import annotations

import json
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

_LIST_LINE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")
_RM_COMMAND = re.compile(r"^(?:git\s+rm|rm)\s+(?P<args>.+)$")

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


@dataclass(frozen=True)
class Segment:
    index: int
    text: str


@dataclass(frozen=True)
class EditEvent:
    rel_path: str
    last_segment_index: int | None


def parse_transcript(path: Path, staged_root: Path) -> tuple[list[Segment], list[EditEvent]]:
    segments: list[Segment] = []
    edits: list[EditEvent] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return segments, edits
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                for text in _split_segments(block.get("text", "")):
                    segments.append(Segment(index=len(segments), text=text))
            elif block.get("type") == "tool_use" and block.get("name") in EDIT_TOOLS:
                rel_path = _to_staged_rel((block.get("input") or {}).get("file_path"), staged_root)
                if rel_path:
                    last_index = len(segments) - 1 if segments else None
                    edits.append(EditEvent(rel_path=rel_path, last_segment_index=last_index))
            elif block.get("type") == "tool_use" and block.get("name") == "Bash":
                command = (block.get("input") or {}).get("command")
                if isinstance(command, str):
                    last_index = len(segments) - 1 if segments else None
                    for rel_path in _bash_deleted_rel_paths(command, staged_root):
                        edits.append(EditEvent(rel_path=rel_path, last_segment_index=last_index))
    return segments, edits


def _bash_deleted_rel_paths(command: str, staged_root: Path) -> list[str]:
    """`git rm`/`rm` (ADR 026) are the two deletion shapes observed in
    dogfooding — deliberately not a general shell-command parser (quoting,
    subshells, aliases would make that open-ended and fragile)."""
    match = _RM_COMMAND.match(command.strip())
    if not match:
        return []
    rel_paths = []
    for token in match.group("args").split():
        if token.startswith("-"):
            continue
        if Path(token).is_absolute():
            rel_path = _to_staged_rel(token, staged_root)
        else:
            # the file is gone by the time the transcript is mined, so
            # ./x.py and a/../b.py must be normalized lexically, not resolved
            rel_path = posixpath.normpath(token)
        if rel_path:
            rel_paths.append(rel_path)
    return rel_paths


def _to_staged_rel(file_path: str | None, staged_root: Path) -> str | None:
    if not file_path:
        return None
    try:
        return Path(file_path).resolve().relative_to(staged_root.resolve()).as_posix()
    except ValueError:
        return None


def _split_segments(text: str) -> list[str]:
    segments = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            segments.append("\n".join(paragraph).strip())
            paragraph.clear()

    for line in text.splitlines():
        if not line.strip():
            flush_paragraph()
        elif _LIST_LINE.match(line):
            flush_paragraph()
            segments.append(line.strip())
        else:
            paragraph.append(line)
    flush_paragraph()
    return segments
