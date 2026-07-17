from graphwerk.rationale.attribution import (
    attribute_files,
    attribute_guidance_bullets,
    attribute_symbols,
    parse_commit_message,
    parse_guidance_bullet,
    reason_justifies,
)
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
        "I'll start by touching `miner.py` to fix the bug.",
        "Some unrelated narration.",
        "Wrapping up: `miner.py` now dedupes entries before writing.",
    )

    result = attribute_files(parsed, ["miner.py"])

    assert result["miner.py"] == "Wrapping up: `miner.py` now dedupes entries before writing."


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
    parsed = segments("Only talked about `cli.py` here.")

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

    long_text = "`cli.py` " + "x" * (MAX_WHY_LEN * 2)
    result = attribute_files(segments(long_text), ["cli.py"])

    assert len(result["cli.py"]) == MAX_WHY_LEN


def test_guidance_bullet_parses_path_symbols_and_reason():
    bullet = parse_guidance_bullet(
        "- `pkg/webhook.py` (`handle`, `Gateway.charge`): wires the two together"
    )

    assert bullet.rel_path == "pkg/webhook.py"
    assert bullet.symbols == ("handle", "Gateway.charge")
    assert bullet.reason == "wires the two together"


def test_guidance_bullet_without_symbols_still_parses():
    bullet = parse_guidance_bullet("- `cli.py`: added the --version flag")

    assert bullet.rel_path == "cli.py"
    assert bullet.symbols == ()
    assert bullet.reason == "added the --version flag"


def test_non_bullet_segment_does_not_parse():
    assert parse_guidance_bullet("Let me touch cli.py next.") is None
    assert parse_guidance_bullet("cli.py: added the --version flag") is None


def test_attribute_guidance_bullets_gives_each_file_its_own_reason():
    parsed = segments(
        "- `cli.py`: added the --version flag",
        "- `pkg/models.py`: new order field",
    )

    result = attribute_guidance_bullets(parsed, {})

    assert result == {
        "cli.py": "added the --version flag",
        "pkg/models.py": "new order field",
    }


def test_attribute_guidance_bullets_assigns_reason_to_listed_symbols():
    parsed = segments("- `pkg/payment.py` (`Gateway.charge`): now retries three times")

    result = attribute_guidance_bullets(parsed, {"pkg/payment.py": ["Gateway.charge", "Gateway.refund"]})

    assert result == {
        "pkg/payment.py": "now retries three times",
        "pkg/payment.py::Gateway.charge": "now retries three times",
    }


def test_attribute_guidance_bullets_ignores_prose_segments():
    parsed = segments("Just some narration mentioning cli.py in passing.")

    assert attribute_guidance_bullets(parsed, {}) == {}


def test_qualified_reference_through_bare_stem_is_excluded():
    parsed = segments("Patched `business_cache._load_business` in the test suite.")

    assert attribute_files(parsed, ["business_cache.py"]) == {}


def test_full_filename_mention_still_attributes_despite_stem_dot_letters_shape():
    parsed = segments("Reference: `webhook.py`.")

    assert attribute_files(parsed, ["webhook.py"]) == {
        "webhook.py": "Reference: `webhook.py`.",
    }


def test_unquoted_common_word_does_not_collide_with_file_stem():
    parsed = segments("the various conversation helpers are still re-exported")

    assert attribute_files(parsed, ["conversation.py"]) == {}


def test_qualified_reference_exclusion_does_not_apply_to_full_path_alternative():
    parsed = segments("See `src/agendabot/webhook.py` for the wiring.")

    assert attribute_files(parsed, ["src/agendabot/webhook.py"]) == {
        "src/agendabot/webhook.py": "See `src/agendabot/webhook.py` for the wiring.",
    }


def test_symbol_reached_only_through_a_qualified_dotted_path_is_not_a_mention():
    parsed = segments(
        "kept the accessor here because tests do "
        '`monkeypatch.setattr("pkg.webhook._load_business", ...)`'
    )
    changed = {"pkg/webhook.py": ["_load_business"], "pkg/business.py": ["_load_business"]}

    assert attribute_symbols(parsed, changed) == {}


def test_deletion_bullet_fallback_reproduces_dogfood_case():
    parsed = segments(
        "- `src/agendabot/webhook.py` → removed (converted to the package above; "
        "`agendabot.webhook:app` and all existing imports/monkeypatches keep "
        "working unchanged)."
    )

    result = attribute_guidance_bullets(parsed, {})

    assert result["src/agendabot/webhook.py"] == (
        "converted to the package above; `agendabot.webhook:app` and all "
        "existing imports/monkeypatches keep working unchanged"
    )


def test_deletion_bullet_fallback_is_not_tried_when_colon_shape_matches():
    parsed = segments("- `old.py`: removed — superseded by new.py")

    result = attribute_guidance_bullets(parsed, {})

    assert result["old.py"] == "removed — superseded by new.py"


def test_deletion_bullet_without_symbols_arg_still_parses():
    from graphwerk.rationale.attribution import parse_deletion_bullet

    bullet = parse_deletion_bullet("- `old.py` → removed (no longer needed).")

    assert bullet.rel_path == "old.py"
    assert bullet.symbols == ()
    assert bullet.reason == "no longer needed"


def test_non_deletion_segment_does_not_parse_as_deletion_bullet():
    from graphwerk.rationale.attribution import parse_deletion_bullet

    assert parse_deletion_bullet("Let me touch cli.py next.") is None
    assert parse_deletion_bullet("- `cli.py`: added the --version flag") is None


def test_reason_justifies_dogfood_regression_cases():
    assert reason_justifies("FastAPI dependency-injection providers.") is False
    assert reason_justifies(
        "shared env-derived flags, split out since several other modules need them."
    ) is True


def test_reason_justifies_recognizes_each_connective_case_insensitively():
    connectives = [
        "because", "since", "so that", "so it", "in order to", "to avoid",
        "given that", "which lets", "which allows",
    ]
    for connective in connectives:
        assert reason_justifies(f"did this {connective.upper()} it matters") is True


def test_reason_justifies_is_false_without_any_connective():
    assert reason_justifies("builds ConversationContext from state/business/time.") is False


def test_reason_justifies_does_not_match_connective_as_a_substring():
    assert reason_justifies("the science fiction module was untouched") is False


def test_commit_message_empty_after_prefix_is_none():
    assert parse_commit_message([Segment(index=0, text="Commit-message:")]) is None
    assert parse_commit_message([Segment(index=0, text="Commit-message:   ")]) is None


def test_commit_message_only_counts_in_the_final_segment():
    segments = [
        Segment(index=0, text="Commit-message: an early draft"),
        Segment(index=1, text="Actually, let me rework that first."),
    ]
    assert parse_commit_message(segments) is None


def test_commit_message_with_no_segments_is_none():
    assert parse_commit_message([]) is None
