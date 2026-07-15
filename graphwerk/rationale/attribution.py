"""Mention-based attribution: which transcript segment explains which file.

ADR 006: a file's rationale is the latest segment that mentions it, so a
session's wrap-up summary naturally beats early planning chatter.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from graphwerk.rationale.transcript import Segment

MAX_WHY_LEN = 700


def attribute_files(segments: list[Segment], rel_paths: list[str]) -> dict[str, str]:
    rationale: dict[str, str] = {}
    for rel_path in rel_paths:
        mention = _mention_pattern(rel_path)
        for segment in segments:
            if mention.search(segment.text):
                rationale[rel_path] = segment.text[:MAX_WHY_LEN]
    return rationale


def _mention_pattern(rel_path: str) -> re.Pattern[str]:
    name = PurePosixPath(rel_path)
    needles = sorted({rel_path, name.name, name.stem}, key=len, reverse=True)
    alternation = "|".join(re.escape(needle) for needle in needles)
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{alternation})(?![A-Za-z0-9_])")
