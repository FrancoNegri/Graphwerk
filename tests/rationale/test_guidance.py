"""Round-trip: SESSION_GUIDANCE's wording actually earns distinct per-file
and per-symbol rationale from the real mention-attribution miner (ADR 006).
If the guidance wording and the miner's matching rules ever drift apart
(e.g. a miner regex tightens), this test is the one that fails.
"""

from __future__ import annotations

import json
from pathlib import Path

from graphwerk.rationale.attribution import (
    parse_commit_message,
    attribute_files,
    attribute_guidance_bullets,
    attribute_symbols,
)
from graphwerk.rationale.guidance import SESSION_GUIDANCE
from graphwerk.rationale.transcript import parse_transcript


def assistant_entry(*blocks) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def edit_block(file_path: Path) -> dict:
    return {"type": "tool_use", "name": "Edit", "input": {"file_path": str(file_path)}}


def write_transcript(path: Path, entries: list) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def test_session_guidance_format_yields_distinct_per_file_and_symbol_rationale(tmp_path):
    staged_root = tmp_path / "staged"
    staged_root.mkdir()
    transcript_path = tmp_path / "session.jsonl"

    write_transcript(transcript_path, [
        assistant_entry(
            text_block("Let me make those changes."),
            edit_block(staged_root / "billing" / "gateway.py"),
            edit_block(staged_root / "cli.py"),
        ),
        assistant_entry(text_block(
            SESSION_GUIDANCE + "\n\n"
            "- `billing/gateway.py` (`Gateway.charge`): retries now survive a flaky network\n"
            "- `cli.py` (`main`): exposes the new --retry flag callers asked for"
        )),
    ])

    segments, edits = parse_transcript(transcript_path, staged_root)
    changed_symbols = {"billing/gateway.py": ["Gateway.charge"], "cli.py": ["main"]}

    files = attribute_files(segments, [edit.rel_path for edit in edits])
    symbols = attribute_symbols(segments, changed_symbols)

    assert files["billing/gateway.py"] == (
        "- `billing/gateway.py` (`Gateway.charge`): retries now survive a flaky network")
    assert files["cli.py"] == (
        "- `cli.py` (`main`): exposes the new --retry flag callers asked for")
    assert files["billing/gateway.py"] != files["cli.py"]

    assert symbols["billing/gateway.py::Gateway.charge"] == files["billing/gateway.py"]
    assert symbols["cli.py::main"] == files["cli.py"]
    assert symbols["billing/gateway.py::Gateway.charge"] != symbols["cli.py::main"]


def test_session_guidance_deletion_shape_is_parsed_and_attributed(tmp_path):
    staged_root = tmp_path / "staged"
    staged_root.mkdir()
    transcript_path = tmp_path / "session.jsonl"

    write_transcript(transcript_path, [
        assistant_entry(text_block(
            SESSION_GUIDANCE + "\n\n"
            "- `old/legacy.py`: removed — replaced by the package added above"
        )),
    ])

    segments, _ = parse_transcript(transcript_path, staged_root)
    result = attribute_guidance_bullets(segments, {})

    assert result["old/legacy.py"] == "removed — replaced by the package added above"


def test_session_guidance_has_a_labeled_describes_vs_justifies_contrast():
    describes_line = next(
        line for line in SESSION_GUIDANCE.splitlines() if "describes only" in line
    )
    justifies_line = next(
        line for line in SESSION_GUIDANCE.splitlines() if line.startswith("- justifies")
    )

    assert "path/to/file.py" in describes_line and "path/to/file.py" in justifies_line
    assert describes_line != justifies_line


def test_session_guidance_closing_line_yields_the_commit_message(tmp_path):
    staged_root = tmp_path / "staged"
    staged_root.mkdir()
    transcript_path = tmp_path / "session.jsonl"

    write_transcript(transcript_path, [
        assistant_entry(text_block(
            SESSION_GUIDANCE + "\n\n"
            "- `billing/gateway.py` (`Gateway.charge`): retries now survive a flaky network\n"
            "\n"
            "Commit-message: Retry flaky network calls in the billing gateway"
        )),
    ])

    segments, _ = parse_transcript(transcript_path, staged_root)
    assert parse_commit_message(segments) == (
        "Retry flaky network calls in the billing gateway")


def test_transcript_without_commit_message_line_yields_none(tmp_path):
    staged_root = tmp_path / "staged"
    staged_root.mkdir()
    transcript_path = tmp_path / "session.jsonl"

    write_transcript(transcript_path, [
        assistant_entry(text_block(
            "- `cli.py` (`main`): exposes the new --retry flag callers asked for"
        )),
    ])

    segments, _ = parse_transcript(transcript_path, staged_root)
    assert parse_commit_message(segments) is None
