"""Mention-based attribution: which transcript segment explains which file.

ADR 006: a file's rationale is the latest segment that mentions it, so a
session's wrap-up summary naturally beats early planning chatter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from graphwerk.rationale.transcript import Segment

MAX_WHY_LEN = 700

_GUIDANCE_BULLET = re.compile(
    r"^[-*]\s*`(?P<path>[^`]+)`\s*(?:\((?P<symbols>[^)]*)\))?\s*:\s*(?P<reason>.+)$"
)
_DELETION_BULLET = re.compile(
    r"^[-*]\s*`(?P<path>[^`]+)`\s*(?:→|->)\s*removed\b\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
_BACKTICKED = re.compile(r"`([^`]+)`")

_JUSTIFYING_CONNECTIVES = (
    "because", "since", "so that", "so it", "in order to", "to avoid",
    "given that", "which lets", "which allows",
)
_JUSTIFYING_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(c) for c in _JUSTIFYING_CONNECTIVES) + r")\b",
    re.IGNORECASE,
)


def reason_justifies(reason: str) -> bool:
    """A cheap heuristic (ADR 027): a reason with no causal/justifying
    connective is very likely describing the code rather than arguing for
    the change. Imprecise by design — a nudge, not a judgment."""
    return bool(_JUSTIFYING_PATTERN.search(reason))


@dataclass(frozen=True)
class GuidanceBullet:
    """One `SESSION_GUIDANCE`-shaped line (ADR 012), parsed directly."""

    rel_path: str
    symbols: tuple[str, ...]
    reason: str


def parse_guidance_bullet(text: str) -> GuidanceBullet | None:
    match = _GUIDANCE_BULLET.match(text.strip())
    if not match:
        return None
    symbols = tuple(_BACKTICKED.findall(match.group("symbols") or ""))
    return GuidanceBullet(
        rel_path=match.group("path"),
        symbols=symbols,
        reason=match.group("reason").strip(),
    )


def parse_deletion_bullet(text: str) -> GuidanceBullet | None:
    """Fallback shape for a deleted file (ADR 026): `` `path` → removed (...) ``.
    Only tried where the primary colon shape (`parse_guidance_bullet`)
    doesn't match, so a cooperative session that follows `SESSION_GUIDANCE`
    exactly is unaffected."""
    match = _DELETION_BULLET.match(text.strip())
    if not match:
        return None
    reason = match.group("rest").strip().rstrip(".").strip()
    if reason.startswith("(") and reason.endswith(")"):
        reason = reason[1:-1].strip()
    return GuidanceBullet(rel_path=match.group("path"), symbols=(), reason=reason or "removed")


def attribute_guidance_bullets(segments: list[Segment],
                               symbols_by_file: dict[str, list[str]]) -> dict[str, str]:
    """Highest-priority rationale source (ADR 025): a segment in the guidance
    bullet shape names its own file/symbols directly, so a later segment that
    only repeats the filename in passing can't shadow it."""
    rationale: dict[str, str] = {}
    for segment in segments:
        bullet = parse_guidance_bullet(segment.text) or parse_deletion_bullet(segment.text)
        if not bullet:
            continue
        rationale[bullet.rel_path] = bullet.reason
        for qualname in symbols_by_file.get(bullet.rel_path, []):
            bare_name = qualname.split(".")[-1]
            if bare_name in bullet.symbols or qualname in bullet.symbols:
                rationale[f"{bullet.rel_path}::{qualname}"] = bullet.reason
    return rationale


def attribute_files(segments: list[Segment], rel_paths: list[str]) -> dict[str, str]:
    rationale: dict[str, str] = {}
    for rel_path in rel_paths:
        for segment in segments:
            if _file_mentioned(segment.text, rel_path):
                rationale[rel_path] = segment.text[:MAX_WHY_LEN]
    return rationale


def _file_mentioned(text: str, rel_path: str) -> bool:
    """A file counts as mentioned only inside a backtick-quoted span —
    prose narration doesn't reliably distinguish a genuine reference from
    an ordinary word matching the file's stem (ADR 025). A bare-stem match
    immediately followed by `.<identifier>` is excluded too (a qualified
    reference *through* the file, e.g. `business_cache._load_business`,
    not narration about the file itself) — but the file's own full name or
    path is a genuine reference either way, even though it has the same
    "letters, dot, letters" shape."""
    name = PurePosixPath(rel_path)
    full_names = {rel_path, name.name}
    full_pattern = _distinct_token_pattern(_alternation(full_names))
    stem_pattern = None if name.stem in full_names else _distinct_token_pattern(re.escape(name.stem))
    for span in _BACKTICKED.findall(text):
        if full_pattern.search(span):
            return True
        if stem_pattern:
            for match in stem_pattern.finditer(span):
                if not _is_qualified_reference(span, match.end()):
                    return True
    return False


def _is_qualified_reference(span: str, end: int) -> bool:
    return span[end:end + 1] == "." and span[end + 1:end + 2].isidentifier()


def _alternation(needles: set[str]) -> str:
    return "|".join(re.escape(needle) for needle in sorted(needles, key=len, reverse=True))


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
            for segment in segments:
                if not _symbol_mentioned(segment.text, qualname):
                    continue
                if len(files_sharing_name[name]) > 1 and not _names_only_this_file(
                        segment.text, rel_path, files_sharing_name[name]):
                    continue
                rationale[f"{rel_path}::{qualname}"] = segment.text[:MAX_WHY_LEN]
    return rationale


def _symbol_mentioned(text: str, qualname: str) -> bool:
    """A bare symbol name preceded by a dot only counts as a mention when
    that dot is the symbol's own `Class.method` qualifier. Any other
    dotted prefix (e.g. `agendabot.webhook._load_business`, an old import
    path preserved in a monkeypatch string) names some other module's
    reference to the symbol, not narration about the file that owns it
    (ADR 025, recurring at the symbol level)."""
    name = qualname.split(".")[-1]
    own_prefix = qualname.rsplit(".", 1)[0] + "." if "." in qualname else None
    pattern = _distinct_token_pattern(re.escape(name))
    for match in pattern.finditer(text):
        preceding = text[:match.start()]
        if preceding[-1:] != ".":
            return True
        if own_prefix and preceding.endswith(own_prefix):
            return True
    return False


def _names_only_this_file(text: str, rel_path: str, candidates: set[str]) -> bool:
    mentioned = [rel for rel in candidates if _mention_pattern(rel).search(text)]
    return mentioned == [rel_path]


def _mention_pattern(rel_path: str) -> re.Pattern[str]:
    name = PurePosixPath(rel_path)
    needles = sorted({rel_path, name.name, name.stem}, key=len, reverse=True)
    return _distinct_token_pattern("|".join(re.escape(needle) for needle in needles))


def _distinct_token_pattern(escaped_alternation: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_])(?:{escaped_alternation})(?![A-Za-z0-9_])")
