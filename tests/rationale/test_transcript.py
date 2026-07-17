import json
from pathlib import Path

import pytest

from graphwerk.rationale.transcript import parse_transcript


@pytest.fixture
def staged_root(tmp_path):
    staged = tmp_path / "staging"
    staged.mkdir()
    return staged


def assistant_entry(*blocks) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def edit_block(file_path: Path, tool: str = "Edit") -> dict:
    return {"type": "tool_use", "name": tool, "input": {"file_path": str(file_path)}}


def write_jsonl(path: Path, entries: list) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def test_multi_paragraph_text_block_splits_into_ordered_segments(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(text_block(
            "First I looked at the widget.\n\nThen I refactored it\nacross two lines."
        )),
        assistant_entry(text_block("A later thought.")),
    ])

    segments, edits = parse_transcript(transcript, staged_root)

    assert [segment.text for segment in segments] == [
        "First I looked at the widget.",
        "Then I refactored it\nacross two lines.",
        "A later thought.",
    ]
    assert [segment.index for segment in segments] == [0, 1, 2]
    assert edits == []


def test_bullet_list_lines_become_their_own_segments(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(text_block(
            "Summary of the session:\n"
            "- `cli.py`: added the --version flag\n"
            "* `models.py`: new order field\n"
            "1. checked the demo still runs"
        )),
    ])

    segments, _ = parse_transcript(transcript, staged_root)

    assert [segment.text for segment in segments] == [
        "Summary of the session:",
        "- `cli.py`: added the --version flag",
        "* `models.py`: new order field",
        "1. checked the demo still runs",
    ]


def test_edits_interleaved_with_narration_anchor_to_the_preceding_segment(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(edit_block(staged_root / "early.py", tool="Write")),
        assistant_entry(
            text_block("Fixing the widget."),
            edit_block(staged_root / "pkg" / "widget.py"),
        ),
        assistant_entry(text_block("Now the CLI.\n\nAdding the flag.")),
        assistant_entry(edit_block(staged_root / "cli.py")),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [(edit.rel_path, edit.last_segment_index) for edit in edits] == [
        ("early.py", None),
        ("pkg/widget.py", 0),
        ("cli.py", 2),
    ]


def test_malformed_lines_and_out_of_root_paths_are_skipped(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    entries = [
        assistant_entry(text_block("Real narration."), edit_block(staged_root / "foo.py")),
        assistant_entry(edit_block(tmp_path / "elsewhere" / "outside.py")),
    ]
    transcript.write_text(
        "not json at all\n"
        + json.dumps(entries[0]) + "\n"
        + '{"message": {"content": "just a string"}}\n'
        + json.dumps(entries[1]) + "\n",
        encoding="utf-8",
    )

    segments, edits = parse_transcript(transcript, staged_root)

    assert [segment.text for segment in segments] == ["Real narration."]
    assert [edit.rel_path for edit in edits] == ["foo.py"]


def bash_block(command: str) -> dict:
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def test_git_rm_bash_call_becomes_an_edit_event(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(
            text_block("Removing the old module."),
            bash_block(f"git rm {staged_root / 'old.py'}"),
        ),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [(edit.rel_path, edit.last_segment_index) for edit in edits] == [("old.py", 0)]


def test_plain_rm_bash_call_becomes_an_edit_event(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(
            text_block("Removing the old module."),
            bash_block(f"rm {staged_root / 'old.py'}"),
        ),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [(edit.rel_path, edit.last_segment_index) for edit in edits] == [("old.py", 0)]


def test_git_rm_with_multiple_paths_emits_an_event_per_path(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(
            bash_block(f"git rm {staged_root / 'a.py'} {staged_root / 'b.py'}"),
        ),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert {edit.rel_path for edit in edits} == {"a.py", "b.py"}


def test_rm_with_dot_slash_prefix_normalizes_to_node_path(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(
            text_block("Removing the old module."),
            bash_block("rm ./old.py"),
        ),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [(edit.rel_path, edit.last_segment_index) for edit in edits] == [("old.py", 0)]


def test_git_rm_with_dot_slash_prefix_normalizes_to_node_path(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(bash_block("git rm ./sub/old.py")),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [edit.rel_path for edit in edits] == ["sub/old.py"]


def test_rm_with_parent_traversal_token_normalizes_lexically(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(bash_block("rm sub/../old.py")),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [edit.rel_path for edit in edits] == ["old.py"]


def test_rm_with_plain_relative_token_keeps_it_as_is(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(bash_block("rm src/x.py")),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert [edit.rel_path for edit in edits] == ["src/x.py"]


def test_bash_call_unrelated_to_rm_produces_no_edit_event(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(bash_block("pytest -q")),
    ])

    _, edits = parse_transcript(transcript, staged_root)

    assert edits == []


def test_bash_deleted_file_is_eligible_for_prose_mention_attribution(tmp_path, staged_root):
    """Reproduces ADR 026's third gap: a deletion narrated only in prose (no
    dedicated bullet at all) still gets attributed, because the `git rm` call
    now enters `rel_paths` the same as an Edit/Write-touched file."""
    from graphwerk.rationale.attribution import attribute_files

    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        assistant_entry(
            bash_block(f"git rm {staged_root / 'old.py'}"),
        ),
        assistant_entry(text_block(
            "Removed `old.py` since its logic moved into the new package."
        )),
    ])

    segments, edits = parse_transcript(transcript, staged_root)
    result = attribute_files(segments, sorted({edit.rel_path for edit in edits}))

    assert result["old.py"] == "Removed `old.py` since its logic moved into the new package."


def test_non_assistant_entries_and_other_tools_are_ignored(tmp_path, staged_root):
    transcript = tmp_path / "session.jsonl"
    write_jsonl(transcript, [
        {"type": "user", "message": {"role": "user", "content": [
            text_block("User words, not rationale."),
        ]}},
        assistant_entry(
            {"type": "tool_use", "name": "Bash", "input": {"file_path": str(staged_root / "foo.py")}},
            text_block("Assistant words."),
        ),
    ])

    segments, edits = parse_transcript(transcript, staged_root)

    assert [segment.text for segment in segments] == ["Assistant words."]
    assert edits == []
