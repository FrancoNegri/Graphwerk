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


def attribute_symbols(segments: list[Segment],
                      symbols_by_file: dict[str, list[str]]) -> dict[str, str]:
    files_sharing_name: dict[str, set[str]] = {}
    for rel_path, qualnames in symbols_by_file.items():
        for qualname in qualnames:
            files_sharing_name.setdefault(qualname.split(".")[-1], set()).add(rel_path)

    rationale: dict[str, str] = {}
    for rel_path, qualnames in symbols_by_file.items():
        for qualname in qualnames:
            name = qualname.split(".")[-1]
            mention = _distinct_token_pattern(re.escape(name))
            for segment in segments:
                if not mention.search(segment.text):
                    continue
                if len(files_sharing_name[name]) > 1 and not _names_only_this_file(
                        segment.text, rel_path, files_sharing_name[name]):
                    continue
                rationale[f"{rel_path}::{qualname}"] = segment.text[:MAX_WHY_LEN]
    return rationale


def _names_only_this_file(text: str, rel_path: str, candidates: set[str]) -> bool:
    mentioned = [rel for rel in candidates if _mention_pattern(rel).search(text)]
    return mentioned == [rel_path]


def _mention_pattern(rel_path: str) -> re.Pattern[str]:
    name = PurePosixPath(rel_path)
    needles = sorted({rel_path, name.name, name.stem}, key=len, reverse=True)
    return _distinct_token_pattern("|".join(re.escape(needle) for needle in needles))


def _distinct_token_pattern(escaped_alternation: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{escaped_alternation})(?![A-Za-z0-9_])")
