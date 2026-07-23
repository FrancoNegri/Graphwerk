"""Symbol extraction for Markdown files: one heading, one SymbolInfo.

Same FileIndex/SymbolInfo contract PythonAstExtractor implements — stdlib
line-based heading scan, no CommonMark dependency (ADR 046).
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

from graphwerk.models import FileIndex, SymbolInfo

_HEADING = re.compile(r"^(#{2,})\s+(.+?)\s*$")
_INLINE_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_DECISION_LINE = re.compile(r"^Decision:\s*(\S+\.md)\s*$", re.MULTILINE)


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
        index.references = _extract_references(source, rel_path)
        index.decision_ref = _extract_decision_ref(source)
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


def _extract_references(source: str, rel_path: str) -> set[str]:
    """Resolves inline `[text](path.md)` links (relative to this file's own
    directory) to repo-root-relative target paths — the deterministic
    doc-to-doc link-parsing ADR 046 chose over inferred semantic
    relationships. The `Decision:` line is deliberately excluded (ADR
    065): it's a distinct, unambiguous signal, not an arbitrary mention —
    see `_extract_decision_ref`."""
    inline_targets = [match.group(1) for match in _INLINE_LINK.finditer(source)]
    resolved = {_resolve_relative_link(rel_path, target) for target in inline_targets}
    resolved.discard(None)
    return resolved


def _extract_decision_ref(source: str) -> str | None:
    """The repo-root-relative target of this file's own
    `Decision: docs/decisions/NNN-....md` line (already repo-root-relative,
    as every ticket file writes it), or None if it has none. ADR 065
    promotes this out of `references` into its own `implements` edge."""
    match = _DECISION_LINE.search(source)
    return None if match is None else _resolve_rooted_link(match.group(1))


def _resolve_relative_link(source_rel_path: str, link_target: str) -> str | None:
    target = _validated_md_target(link_target)
    if target is None:
        return None
    directory = posixpath.dirname(source_rel_path)
    return posixpath.normpath(posixpath.join(directory, target))


def _resolve_rooted_link(link_target: str) -> str | None:
    target = _validated_md_target(link_target)
    return None if target is None else posixpath.normpath(target)


def _validated_md_target(link_target: str) -> str | None:
    target = link_target.split("#", 1)[0]
    if not target.endswith(".md") or "://" in target or target.startswith("/"):
        return None
    return target
