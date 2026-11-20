"""Tests for the text on a Telescope Access card.

The page is a Jinja template inside ``contributed-telescope.rst``. Each test
copies the invented fixture data to a temporary folder, changes the one
telescope record, renders the page's telescope block with Jinja alone (no
Sphinx) and looks at the resulting reStructuredText. That covers what a card
says (observing mode, process note, header, contacts) without a full build.
"""

import datetime
import io
import shutil

import jinja2
import yaml
from docutils import nodes
from docutils.core import publish_doctree

from ikp_data.loaders import build_contexts
from ikp_data.loaders.telescopes import _rst_plain_text
from tests.test_card_page_templates import FIXTURE_DATA_DIR, jinja_block, read_structure

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


def test_header_says_tbd_without_an_aperture(tmp_path):
    text = render_card_text(tmp_path, contribution_id="AAA-BBB-S1", aperture=None)
    assert "AAA-BBB-S1 · TBD — " in text


def test_missing_values_read_tbd_never_tba(tmp_path):
    """Every fallback on the page (header, semester, time, duration, table cells) says TBD."""
    # The schema requires these fields, so real data never reaches the fallbacks
    # this way; the test renders without validation to exercise them directly.
    text = render_card_text(
        tmp_path,
        aperture=None,
        instrumentation=[],
        first_semester=None,
        time_available=None,
        duration=None,
    )
    assert "TBA" not in text
    assert "**First semester:** TBD" in text
    assert "**Time available:** TBD" in text
    assert "**Duration:** TBD" in text
    assert text.count("<td>TBD</td>") == 2  # the instrumentation and aperture cells


def test_search_index_still_finds_a_card_by_its_id(tmp_path):
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    context = build_contexts(data_dir, today=TODAY)["contributed_telescopes"]
    assert "tst-fix-s1" in context["search_index_json"].lower()


def test_contact_note_follows_the_contact(tmp_path):
    contacts = [{"name": "Pat", "email": "pat@example.org", "note": "ask about eligibility"}]
    text = render_card_text(tmp_path, contacts=contacts)
    assert "Pat (`pat@example.org <mailto:pat@example.org>`_) — ask about eligibility" in text


def test_contact_without_a_note_shows_no_dash(tmp_path):
    contacts = [{"name": "Pat", "email": "pat@example.org"}]
    text = render_card_text(tmp_path, contacts=contacts)
    assert "(`pat@example.org <mailto:pat@example.org>`_)\n" in text


def test_contact_note_cannot_inject_markup(tmp_path):
    # Every punctuation character in a note is backslash-escaped, so these
    # reStructuredText constructs reach the page as literal text.
    hostile = "<b>bold</b> *emph* `lit` |sub| :role:`x` [ref]_ <http://evil.example>`_"
    contacts = [{"name": "Pat", "email": "pat@example.org", "note": hostile}]
    text = render_card_text(tmp_path, contacts=contacts)
    note_line = next(line for line in text.splitlines() if "**Contact:**" in line)
    note = note_line.split(" — ", 1)[1]
    # Every one of these characters is preceded by a backslash.
    for char in "<>*`|:[]_":
        for index, found in enumerate(note):
            if found == char:
                assert note[index - 1] == "\\", f"unescaped {char!r} in {note!r}"


def test_note_text_is_otherwise_unchanged(tmp_path):
    contacts = [{"name": "Pat", "email": "pat@example.org", "note": "line one\n  line two"}]
    text = render_card_text(tmp_path, contacts=contacts)
    assert "— line one line two" in text


def test_card_without_contacts_points_to_the_helpdesk(tmp_path):
    text = render_card_text(tmp_path, contacts=[])
    assert "Questions: email the in-kind helpdesk (see the top of this page)." in text
    assert "**Contact:**" not in text


def test_card_with_a_contact_has_no_helpdesk_line(tmp_path):
    text = render_card_text(tmp_path)
    assert "Questions: email the in-kind helpdesk" not in text


def test_contacts_are_joined_by_semicolons_when_any_has_a_note(tmp_path):
    contacts = [
        {"name": "Pat", "email": "pat@example.org", "note": "ask about eligibility"},
        {"name": "Sam", "email": "sam@example.org"},
    ]
    text = render_card_text(tmp_path / "with-note", contacts=contacts)
    assert "ask about eligibility; Sam (" in text


def test_contacts_are_joined_by_commas_when_none_has_a_note(tmp_path):
    contacts = [
        {"name": "Pat", "email": "pat@example.org"},
        {"name": "Sam", "email": "sam@example.org"},
    ]
    text = render_card_text(tmp_path, contacts=contacts)
    assert "_), Sam (" in text


def test_escaped_note_parses_back_to_the_same_text():
    """docutils reads the escaped text as one paragraph equal to the input, with no warnings."""
    inputs = [
        "ends with a backslash \\",
        "double colon :: here",
        "see https://example.org/a_b?x=1&y=*2*",
        "mail someone@example.org today",
        "*emph* and **strong**",
        ":ref:`target` and `lit`",
        "|sub| and [ref]_ and word_",
        ".. note:: looks like a directive",
        "Maša Lakićević: queries — ünïcode",
    ]
    for text in inputs:
        warnings = io.StringIO()
        doctree = publish_doctree(
            _rst_plain_text(text),
            settings_overrides={"report_level": 1, "halt_level": 5, "warning_stream": warnings},
        )
        paragraphs = list(doctree.findall(nodes.paragraph))
        assert len(doctree.children) == 1 and len(paragraphs) == 1, text
        assert paragraphs[0].astext() == text, text
        assert warnings.getvalue() == "", (text, warnings.getvalue())


def test_aperture_header_asks_for_a_numeric_sort_by_the_row_value(tmp_path):
    text = render_card_text(tmp_path)
    assert '<th data-sort="aperture-value" data-sort-type="number">Aperture</th>' in text


def test_rows_carry_the_aperture_value_and_leave_it_blank_without_one(tmp_path):
    with_size = read_structure(render_card_text(tmp_path / "a", aperture="2 x 8.4m")).rows[0]
    assert with_size["data-aperture-value"] == "8.4"
    without_size = read_structure(render_card_text(tmp_path / "b", aperture=None)).rows[0]
    assert without_size["data-aperture-value"] == ""
