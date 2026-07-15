from graphwerk.rationale.attribution import attribute_files
from graphwerk.rationale.transcript import Segment


def segments(*texts: str) -> list[Segment]:
    return [Segment(index=i, text=text) for i, text in enumerate(texts)]


def test_bullet_summary_attributes_each_file_to_its_own_line():
    parsed = segments(
        "Let me make those changes.",
        "- `cli.py`: added the --version flag",
        "- `pkg/models.py`: new order field",
    )

    result = attribute_files(parsed, ["cli.py", "pkg/models.py"])

    assert result == {
        "cli.py": "- `cli.py`: added the --version flag",
        "pkg/models.py": "- `pkg/models.py`: new order field",
    }


def test_latest_mention_wins():
    parsed = segments(
        "I'll start by touching miner.py to fix the bug.",
        "Some unrelated narration.",
        "Wrapping up: miner.py now dedupes entries before writing.",
    )

    result = attribute_files(parsed, ["miner.py"])

    assert result["miner.py"] == "Wrapping up: miner.py now dedupes entries before writing."


def test_stem_matches_as_a_distinct_token_not_a_substring():
    parsed = segments(
        "The determiner logic was already fine.",
        "Renamed refined_miner elsewhere.",
    )
    assert attribute_files(parsed, ["pkg/miner.py"]) == {}

    mentioned = segments("Tightened up miner so it skips blanks (see `miner`).")
    result = attribute_files(mentioned, ["pkg/miner.py"])
    assert result["pkg/miner.py"] == "Tightened up miner so it skips blanks (see `miner`)."


def test_unmentioned_files_are_absent():
    parsed = segments("Only talked about cli.py here.")

    result = attribute_files(parsed, ["cli.py", "models.py"])

    assert "models.py" not in result
    assert set(result) == {"cli.py"}


def test_rationale_is_truncated_to_max_why_len():
    from graphwerk.rationale.attribution import MAX_WHY_LEN

    long_text = "cli.py " + "x" * (MAX_WHY_LEN * 2)
    result = attribute_files(segments(long_text), ["cli.py"])

    assert len(result["cli.py"]) == MAX_WHY_LEN
