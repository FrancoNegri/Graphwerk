"""Symbol extraction for Markdown files: one heading, one SymbolInfo.

Same FileIndex/SymbolInfo contract PythonAstExtractor implements — stdlib
line-based heading scan, no CommonMark dependency (ADR 046).
"""

from __future__ import annotations

import re
from pathlib import Path

from graphwerk.models import FileIndex, SymbolInfo

_HEADING = re.compile(r"^(#{2,})\s+(.+?)\s*$")


class MarkdownExtractor:
    """Extracts level-2-and-deeper headings as sections of one file."""

    def extract(self, file_path: Path, rel_path: str) -> FileIndex:
        index = FileIndex(rel_path=rel_path)
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            index.parse_error = f"{type(exc).__name__}: {exc}"
            return index

        lines = source.splitlines(keepends=True)
        headings = [
            (lineno, len(match.group(1)), match.group(2))
            for lineno, line in enumerate(lines)
            if (match := _HEADING.match(line))
        ]

        seen_counts: dict[str, int] = {}
        for position, (start, level, text) in enumerate(headings):
            end = _section_end(headings, position, len(lines))
            qualname = _unique_qualname(text, seen_counts)
            index.symbols[qualname] = SymbolInfo(
                qualname=qualname,
                kind="heading",
                lineno=start + 1,
                end_lineno=end,
                source="".join(lines[start:end]),
            )
        return index


def _section_end(headings: list[tuple[int, int, str]], position: int, file_length: int) -> int:
    _, level, _ = headings[position]
    for next_start, next_level, _ in headings[position + 1:]:
        if next_level <= level:
            return next_start
    return file_length


def _unique_qualname(text: str, seen_counts: dict[str, int]) -> str:
    seen_counts[text] = seen_counts.get(text, 0) + 1
    count = seen_counts[text]
    return text if count == 1 else f"{text} ({count})"
