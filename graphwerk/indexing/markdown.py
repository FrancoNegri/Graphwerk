"""Symbol extraction for Markdown files: one heading, one SymbolInfo.

Same FileIndex/SymbolInfo contract PythonAstExtractor implements — stdlib
line-based heading scan, no CommonMark dependency (ADR 046).
"""

from __future__ import annotations

import logging
import posixpath
import re
from pathlib import Path

from graphwerk.models import FileIndex, SymbolInfo

_HEADING = re.compile(r"^(#{2,})\s+(.+?)\s*$")
_INLINE_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_DECISION_LINE = re.compile(r"^Decision:\s*(\S+\.md)\s*$", re.MULTILINE)
_ADR_RELATIONSHIP_LINE = re.compile(
    r"^(Supersedes|Amends|Extends):[ \t]*(.+?)[ \t]*$", re.MULTILINE
)
_DECISIONS_DIR = "docs/decisions/"

_logger = logging.getLogger(__name__)


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
        index.adr_relationships = _extract_adr_relationships(source, file_path, rel_path)
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
    """Resolves both inline `[text](path.md)` links (relative to this file's
    own directory) and the `Decision: docs/decisions/NNN-....md` line
    (already repo-root-relative, as every ticket file writes it) to
    repo-root-relative target paths — the deterministic doc-to-doc
    link-parsing ADR 046 chose over inferred semantic relationships."""
    inline_targets = [match.group(1) for match in _INLINE_LINK.finditer(source)]
    resolved = {_resolve_relative_link(rel_path, target) for target in inline_targets}
    resolved |= {_resolve_rooted_link(target) for target in _DECISION_LINE.findall(source)}
    resolved.discard(None)
    return resolved


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


def _extract_adr_relationships(
    source: str, file_path: Path, rel_path: str
) -> dict[str, set[str]]:
    """Parses the `Supersedes:`/`Amends:`/`Extends:` ADR front-matter
    convention (ADR 065) into kind -> target ADR paths. ADR-specific by
    design (see ADR 065's rejected "mine ADR NNN mentions in prose"
    alternative) — a same-shaped line outside docs/decisions/ is ignored."""
    if not rel_path.startswith(_DECISIONS_DIR):
        return {}

    repo_root = _repo_root(file_path, rel_path)
    relationships: dict[str, set[str]] = {}
    for kind_text, targets_text in _ADR_RELATIONSHIP_LINE.findall(source):
        targets = {
            resolved
            for raw_number in targets_text.split(",")
            if (resolved := _resolve_adr_number(repo_root, raw_number.strip())) is not None
        }
        if targets:
            relationships.setdefault(kind_text.lower(), set()).update(targets)
    return relationships


def _repo_root(file_path: Path, rel_path: str) -> Path:
    """`file_path` mirrors `rel_path` under the repo root for a real
    on-disk read (`WorkingTreeRevision`); walking up one parent per
    `rel_path` path component lands back at that root."""
    root = file_path
    for _ in Path(rel_path).parts:
        root = root.parent
    return root


def _resolve_adr_number(repo_root: Path, raw_number: str) -> str | None:
    if not raw_number.isdigit():
        return None
    matches = sorted(repo_root.glob(f"{_DECISIONS_DIR}{raw_number}-*.md"))
    if not matches:
        _logger.warning(
            "ADR relationship target %r not found (%s%s-*.md)",
            raw_number,
            _DECISIONS_DIR,
            raw_number,
        )
        return None
    return posixpath.normpath(matches[0].relative_to(repo_root).as_posix())
