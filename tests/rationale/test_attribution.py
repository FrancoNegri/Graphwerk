from graphwerk.rationale.attribution import attribute_files, attribute_symbols
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


def test_symbol_mention_yields_qualname_entry_latest_wins():
    parsed = segments(
        "First pass: charge gets a retry loop.",
        "Final: charge now retries three times with backoff.",
        "Unrelated closing remark.",
    )

    result = attribute_symbols(parsed, {"pkg/payment.py": ["PaymentGateway.charge"]})

    assert result == {
        "pkg/payment.py::PaymentGateway.charge":
            "Final: charge now retries three times with backoff.",
    }


def test_symbol_name_must_be_a_distinct_token():
    parsed = segments("The supercharger and charged paths are untouched.")

    assert attribute_symbols(parsed, {"pkg/payment.py": ["PaymentGateway.charge"]}) == {}


def test_same_name_in_two_files_needs_a_file_mention_to_count():
    changed = {"jobs/worker.py": ["Worker.run"], "jobs/scheduler.py": ["Scheduler.run"]}

    unqualified = segments("Tightened up run to exit cleanly.")
    assert attribute_symbols(unqualified, changed) == {}

    both_files = segments("run changed in worker.py and scheduler.py.")
    assert attribute_symbols(both_files, changed) == {}

    one_file = segments("In worker.py, run now exits cleanly.")
    assert attribute_symbols(one_file, changed) == {
        "jobs/worker.py::Worker.run": "In worker.py, run now exits cleanly.",
    }


def test_rationale_is_truncated_to_max_why_len():
    from graphwerk.rationale.attribution import MAX_WHY_LEN

    long_text = "cli.py " + "x" * (MAX_WHY_LEN * 2)
    result = attribute_files(segments(long_text), ["cli.py"])

    assert len(result["cli.py"]) == MAX_WHY_LEN
