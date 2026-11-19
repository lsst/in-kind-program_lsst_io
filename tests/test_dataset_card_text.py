"""Tests for the text on a Datasets card.

The page is a Jinja template inside ``contributed-datasets.rst``. Each test
copies the invented fixture data to a temporary folder, changes the one dataset
record, renders the page's block with Jinja alone (no Sphinx) and looks at the
resulting reStructuredText. That covers what a card says and in which order,
without a full build.
"""

import datetime
import shutil

import jinja2
import yaml

from ikp_data.loaders import build_contexts
from tests.test_card_page_templates import FIXTURE_DATA_DIR, jinja_block

TODAY = datetime.date(2027, 3, 15)

# The rows shown on an Available card before "Show more", in page order.
SHOWN_LABELS = [
    "**Primary recipient:**",
    "**Target audience:**",
    "**Access:**",
    "**Documentation:**",
    "**Support channel:**",
]
# The rows behind "Show more", in page order.
HIDDEN_LABELS = [
    "**Data volume:**",
    "**Hosting location:**",
    "**Citation:**",
    "**Maintenance plan:**",
    "**Data schema:**",
    "**Access mechanisms:**",
    "**Authentication:**",
    "**Generation methods:**",
    "**Validation & limitations:**",
]


def render_card_text(tmp_path, form_data=None, curated=None, **top_level):
    """Render the Datasets block for the fixture record with the given changes.

    `form_data` and `curated` are merged into those sections of the record;
    `top_level` keys (for example ``country``) replace top-level fields.
    """
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    record_path = next((data_dir / "datasets").glob("*.yaml"))
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record["form_data"].update(form_data or {})
    record["curated"].update(curated or {})
    record.update(top_level)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    context = build_contexts(data_dir, today=TODAY)["contributed_datasets"]
    block = jinja_block("contributed-datasets.rst", "contributed_datasets")
    return jinja2.Environment().from_string(block).render(**context)


def card_part(text, start_marker, end_marker):
    """The slice of `text` from `start_marker` up to `end_marker`."""
    return text[text.index(start_marker) : text.index(end_marker)]


def test_summary_comes_first_and_has_no_label(tmp_path):
    text = render_card_text(tmp_path, curated={"summary": "A distinctive summary."})
    summary_at = text.index("A distinctive summary.")
    assert summary_at < text.index("**Primary recipient:**")
    # Nothing but whitespace sits between the badge line and the summary, and the
    # summary line itself has no "Summary:" label.
    line = text[text.rindex("\n", 0, summary_at) + 1 :].split("\n", 1)[0]
    assert line.strip() == "A distinctive summary."
    assert "Summary:" not in text


def test_available_card_rows_are_in_page_order(tmp_path):
    text = render_card_text(tmp_path)
    positions = [text.index(label) for label in SHOWN_LABELS + HIDDEN_LABELS]
    assert positions == sorted(positions)


def test_available_card_hides_the_detail_rows_behind_show_more(tmp_path):
    text = render_card_text(tmp_path)
    container_at = text.index(".. container:: ikp-more-fields")
    for label in SHOWN_LABELS:
        assert text.index(label) < container_at, label
    for label in HIDDEN_LABELS:
        assert text.index(label) > container_at, label
    # The toggle button follows the hidden rows.
    assert text.index("ikp-more-btn") > text.index(HIDDEN_LABELS[-1])


def test_in_progress_card_shows_only_summary_then_recipient_and_no_toggle(tmp_path):
    text = render_card_text(
        tmp_path,
        form_data={"submitted": False},
        curated={"summary": "A distinctive summary."},
    )
    assert text.index("A distinctive summary.") < text.index("**Primary recipient:**")
    for label in SHOWN_LABELS[1:] + HIDDEN_LABELS:
        assert label not in text
    assert "ikp-more-btn" not in text


def test_version_is_shown_between_audience_and_access_when_set(tmp_path):
    text = render_card_text(tmp_path, form_data={"version": "Data Release 2"})
    assert "**Version:** Data Release 2" in text
    assert text.index("**Target audience:**") < text.index("**Version:**") < text.index("**Access:**")


def test_version_row_is_hidden_when_empty(tmp_path):
    assert "**Version:**" not in render_card_text(tmp_path, form_data={"version": None})
    assert "**Version:**" not in render_card_text(tmp_path / "blank", form_data={"version": ""})


def test_version_is_not_shown_on_in_progress_cards(tmp_path):
    text = render_card_text(tmp_path, form_data={"submitted": False, "version": "Data Release 2"})
    assert "**Version:**" not in text


def test_in_progress_status_word_in_table_and_card_badge(tmp_path):
    text = render_card_text(tmp_path, form_data={"submitted": False})
    assert '<span class="ikp-badge ikp-badge-muted">In progress</span>' in text
    assert ":bdg-muted:`In progress`" in text
    assert "Not yet delivered" not in text


def test_available_status_word_is_unchanged(tmp_path):
    text = render_card_text(tmp_path)
    assert '<span class="ikp-badge ikp-badge-success">Available</span>' in text
    assert ":bdg-success:`Available`" in text


def test_status_filter_tokens_keep_their_internal_values(tmp_path):
    text = render_card_text(tmp_path / "a", form_data={"submitted": False})
    assert 'data-filter-status="status-not-yet-delivered"' in text
    assert 'data-status="not_yet_delivered"' in text
    available = render_card_text(tmp_path / "b")
    assert 'data-filter-status="status-available"' in available


def test_uat_badges_use_a_style_distinct_from_data_type_and_wavelength(tmp_path):
    text = render_card_text(
        tmp_path,
        form_data={"data_type": ["Catalog"], "uat_category": ["Astrophysics"]},
        curated={"wavelength_regime": ["Optical"]},
    )
    assert ":bdg-light:`Catalog`" in text
    assert ":bdg-light:`Optical`" in text
    assert ":bdg-primary-line:`Astrophysics`" in text
    assert ":bdg-light:`Astrophysics`" not in text
