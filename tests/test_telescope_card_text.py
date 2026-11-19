"""Tests for the text on a Telescope Access card.

The page is a Jinja template inside ``contributed-telescope.rst``. Each test
copies the invented fixture data to a temporary folder, changes the one
telescope record, renders the page's telescope block with Jinja alone (no
Sphinx) and looks at the resulting reStructuredText. That covers what a card
says (observing mode, process note, header, contacts) without a full build.
"""

import datetime
import shutil

import jinja2
import yaml

from ikp_data.loaders import build_contexts
from tests.test_card_page_templates import FIXTURE_DATA_DIR, jinja_block

TODAY = datetime.date(2027, 3, 15)
SEPARATE_PROCESS_NOTE = (
    "Proposals for this facility follow a separate process from the NOIRLab call; "
    "see the facility links."
)


def render_card_text(tmp_path, **overrides):
    """Render the telescope block for the fixture record with `overrides` applied."""
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    record_path = next((data_dir / "telescopes").glob("*.yaml"))
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record.update(overrides)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    context = build_contexts(data_dir, today=TODAY)["contributed_telescopes"]
    block = jinja_block("contributed-telescope.rst", "contributed_telescopes")
    return jinja2.Environment().from_string(block).render(**context)


def test_observing_mode_is_capitalized_for_display(tmp_path):
    for stored, shown in [("queue", "Queue"), ("service", "Service"), ("mixed", "Mixed")]:
        text = render_card_text(tmp_path / stored, observing_mode=stored)
        assert f"**Observing mode:** {shown}" in text


def test_no_observing_mode_line_when_unset(tmp_path):
    assert "Observing mode" not in render_card_text(tmp_path, observing_mode=None)


def test_process_note_appears_only_for_a_separate_process(tmp_path):
    assert SEPARATE_PROCESS_NOTE in render_card_text(tmp_path / "a", tac_process="special")
    assert SEPARATE_PROCESS_NOTE not in render_card_text(tmp_path / "b", tac_process="default")


def test_header_shows_ids_then_aperture_then_location(tmp_path):
    text = render_card_text(
        tmp_path,
        contribution_id=["AAA-BBB-S1", "CCC-DDD-S2"],
        aperture="10.4m",
        site="La Palma",
        country="Spain",
    )
    assert "AAA-BBB-S1, CCC-DDD-S2 · 10.4m — La Palma, Spain\n" in text
    assert "Contribution ID" not in text


def test_header_says_tba_without_an_aperture(tmp_path):
    text = render_card_text(tmp_path, contribution_id="AAA-BBB-S1", aperture=None)
    assert "AAA-BBB-S1 · TBA — " in text


def test_search_index_still_finds_a_card_by_its_id(tmp_path):
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    context = build_contexts(data_dir, today=TODAY)["contributed_telescopes"]
    assert "tst-fix-s1" in context["search_index_json"].lower()
