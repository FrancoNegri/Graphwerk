"""Merge one node's base and staged text into a single ordered line view."""

import difflib
from dataclasses import dataclass


@dataclass
class CodeLine:
    """One display line: staged-side for ctx/add, base-side for del."""

    text: str
    op: str  # "ctx" | "add" | "del"
    origin_line: int  # 1-based on the side the line came from


def merge_lines(base_text: str | None, staged_text: str | None) -> list[CodeLine]:
    base_lines = (base_text or "").splitlines()
    staged_lines = (staged_text or "").splitlines()
    matcher = difflib.SequenceMatcher(a=base_lines, b=staged_lines, autojunk=False)
    merged: list[CodeLine] = []
    for tag, base_start, base_end, staged_start, staged_end in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            for index in range(base_start, base_end):
                merged.append(CodeLine(base_lines[index], "del", index + 1))
        if tag in ("replace", "insert"):
            for index in range(staged_start, staged_end):
                merged.append(CodeLine(staged_lines[index], "add", index + 1))
        if tag == "equal":
            for index in range(staged_start, staged_end):
                merged.append(CodeLine(staged_lines[index], "ctx", index + 1))
    return merged
