"""Round-trip: DESIGN_SESSION_GUIDANCE's link examples actually match the
markdown extractor's real link-parsing regexes (ticket 126 / ADR 046). If
the guidance wording and the extractor's matching rules ever drift apart,
this test is the one that fails.
"""

from __future__ import annotations

from graphwerk.design_guidance import DESIGN_SESSION_GUIDANCE
from graphwerk.indexing.markdown import _DECISION_LINE, _INLINE_LINK


def test_guidance_grounds_itself_in_the_same_docs_north_star_reads():
    for doc in ("docs/02-product-concept.md", "docs/04-roadmap.md", "CLAUDE.md"):
        assert doc in DESIGN_SESSION_GUIDANCE


def test_guidance_defers_writing_a_document_to_real_decisions_only():
    assert "not for every turn" in DESIGN_SESSION_GUIDANCE
    assert "no change needed" in DESIGN_SESSION_GUIDANCE


def test_guidance_names_the_next_number_check_against_both_readmes():
    assert "docs/decisions/README.md" in DESIGN_SESSION_GUIDANCE
    assert "docs/tickets/README.md" in DESIGN_SESSION_GUIDANCE


def test_guidance_inline_link_example_matches_the_extractors_link_regex():
    matches = _INLINE_LINK.findall(DESIGN_SESSION_GUIDANCE)
    assert "../tickets/NNN-slug.md" in matches


def test_guidance_decision_line_example_matches_the_extractors_decision_regex():
    matches = _DECISION_LINE.findall(DESIGN_SESSION_GUIDANCE)
    assert "docs/decisions/NNN-slug.md" in matches
