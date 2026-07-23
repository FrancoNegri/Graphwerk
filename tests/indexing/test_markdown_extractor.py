from pathlib import Path

from graphwerk.indexing.markdown import MarkdownExtractor


def _extract(tmp_path: Path, source: str, name: str = "doc.md"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return MarkdownExtractor().extract(path, name)


def test_level_two_heading_becomes_a_symbol(tmp_path: Path) -> None:
    index = _extract(tmp_path, "# Title\n\n## Context\n\nSome body text.\n")

    assert list(index.symbols) == ["Context"]
    symbol = index.symbols["Context"]
    assert symbol.kind == "heading"
    assert symbol.qualname == "Context"


def test_level_one_heading_is_not_extracted(tmp_path: Path) -> None:
    index = _extract(tmp_path, "# Title\n\nJust prose, no sections.\n")

    assert index.symbols == {}


def test_deeper_heading_levels_are_extracted(tmp_path: Path) -> None:
    index = _extract(tmp_path, "# Title\n\n### Deep Section\n\nbody\n")

    assert list(index.symbols) == ["Deep Section"]


def test_section_source_runs_to_next_equal_or_shallower_heading(tmp_path: Path) -> None:
    source = (
        "# Title\n\n"
        "## First\n"
        "first body line one\n"
        "first body line two\n"
        "## Second\n"
        "second body\n"
    )
    index = _extract(tmp_path, source)

    assert index.symbols["First"].source == (
        "## First\nfirst body line one\nfirst body line two\n"
    )
    assert index.symbols["Second"].source == "## Second\nsecond body\n"


def test_section_ends_at_shallower_heading_not_just_any_heading(tmp_path: Path) -> None:
    source = (
        "# Title\n\n"
        "## Parent\n"
        "parent intro\n"
        "### Child\n"
        "child body\n"
        "## Sibling\n"
        "sibling body\n"
    )
    index = _extract(tmp_path, source)

    assert index.symbols["Parent"].source == (
        "## Parent\nparent intro\n### Child\nchild body\n"
    )
    assert index.symbols["Child"].source == "### Child\nchild body\n"
    assert index.symbols["Sibling"].source == "## Sibling\nsibling body\n"


def test_section_runs_to_end_of_file_when_no_following_heading(tmp_path: Path) -> None:
    source = "# Title\n\n## Only\nbody line\nmore body\n"
    index = _extract(tmp_path, source)

    assert index.symbols["Only"].source == "## Only\nbody line\nmore body\n"


def test_repeated_heading_text_gets_deduplicated_qualname(tmp_path: Path) -> None:
    source = "# Title\n\n## Notes\nfirst\n## Notes\nsecond\n"
    index = _extract(tmp_path, source)

    assert list(index.symbols) == ["Notes", "Notes (2)"]
    assert index.symbols["Notes"].source == "## Notes\nfirst\n"
    assert index.symbols["Notes (2)"].source == "## Notes\nsecond\n"


def test_file_with_no_headings_has_empty_symbols(tmp_path: Path) -> None:
    index = _extract(tmp_path, "just a plain paragraph, no headings at all.\n")

    assert index.symbols == {}
    assert index.parse_error is None


def test_inline_relative_link_resolves_to_repo_relative_target(tmp_path: Path) -> None:
    index = _extract(
        tmp_path,
        "# Title\n\nSee [the ADR](../decisions/046-thing.md) for context.\n",
        name="tickets/124-thing.md",
    )

    assert index.references == {"decisions/046-thing.md"}


def test_link_anchor_is_stripped_before_resolving(tmp_path: Path) -> None:
    index = _extract(
        tmp_path,
        "# Title\n\nSee [section](../decisions/046-thing.md#decision) here.\n",
        name="tickets/124-thing.md",
    )

    assert index.references == {"decisions/046-thing.md"}


def test_decision_line_is_recognized_as_a_reference(tmp_path: Path) -> None:
    index = _extract(
        tmp_path,
        "# 124. Some ticket\n\nDecision: docs/decisions/046-thing.md\n",
        name="tickets/124-thing.md",
    )

    assert "docs/decisions/046-thing.md" in index.references


def test_external_url_link_is_not_a_reference(tmp_path: Path) -> None:
    index = _extract(
        tmp_path,
        "# Title\n\nSee [docs](https://example.com/page.md) online.\n",
        name="tickets/124-thing.md",
    )

    assert index.references == set()


def test_link_to_non_markdown_target_is_not_a_reference(tmp_path: Path) -> None:
    index = _extract(
        tmp_path,
        "# Title\n\nSee [code](../graphwerk/service.py) for the impl.\n",
        name="tickets/124-thing.md",
    )

    assert index.references == set()


def test_unreadable_file_sets_parse_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"

    index = MarkdownExtractor().extract(missing, "missing.md")

    assert index.parse_error is not None
    assert index.symbols == {}


def _write_adr(tmp_path: Path, name: str, source: str = "# ADR\n") -> None:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def test_supersedes_line_resolves_bare_adr_number_to_its_file(tmp_path: Path) -> None:
    _write_adr(tmp_path, "docs/decisions/037-old-thing.md")
    index = _extract(
        tmp_path,
        "# 058. New thing\n\nStatus: proposed\nSupersedes: 037\n",
        name="docs/decisions/058-new-thing.md",
    )

    assert index.adr_relationships == {"supersedes": {"docs/decisions/037-old-thing.md"}}


def test_amends_and_extends_lines_are_both_recognized(tmp_path: Path) -> None:
    _write_adr(tmp_path, "docs/decisions/058-old-thing.md")
    _write_adr(tmp_path, "docs/decisions/005-split.md")
    index = _extract(
        tmp_path,
        "# 061. Amendment\n\nStatus: proposed\nAmends: 058\nExtends: 005\n",
        name="docs/decisions/061-amendment.md",
    )

    assert index.adr_relationships == {
        "amends": {"docs/decisions/058-old-thing.md"},
        "extends": {"docs/decisions/005-split.md"},
    }


def test_comma_separated_targets_all_resolve(tmp_path: Path) -> None:
    _write_adr(tmp_path, "docs/decisions/037-old-thing.md")
    _write_adr(tmp_path, "docs/decisions/050-other-thing.md")
    index = _extract(
        tmp_path,
        "# 058. New thing\n\nStatus: proposed\nSupersedes: 037, 050\n",
        name="docs/decisions/058-new-thing.md",
    )

    assert index.adr_relationships == {
        "supersedes": {
            "docs/decisions/037-old-thing.md",
            "docs/decisions/050-other-thing.md",
        }
    }


def test_unmatched_adr_number_is_skipped_but_logged(tmp_path, caplog) -> None:
    index = _extract(
        tmp_path,
        "# 058. New thing\n\nStatus: proposed\nSupersedes: 999\n",
        name="docs/decisions/058-new-thing.md",
    )

    assert index.adr_relationships == {}
    assert any("999" in record.message for record in caplog.records)


def test_relationship_line_outside_decisions_dir_is_ignored(tmp_path: Path) -> None:
    _write_adr(tmp_path, "docs/decisions/037-old-thing.md")
    index = _extract(
        tmp_path,
        "# 191. Some ticket\n\nSupersedes: 037\n",
        name="docs/tickets/191-some-ticket.md",
    )

    assert index.adr_relationships == {}


def test_adr_relationship_parsing_does_not_affect_existing_references(tmp_path: Path) -> None:
    _write_adr(tmp_path, "docs/decisions/046-thing.md")
    index = _extract(
        tmp_path,
        "# 058. New thing\n\nDecision: docs/decisions/046-thing.md\nSupersedes: 046\n",
        name="docs/decisions/058-new-thing.md",
    )

    assert index.references == {"docs/decisions/046-thing.md"}
    assert index.adr_relationships == {"supersedes": {"docs/decisions/046-thing.md"}}
