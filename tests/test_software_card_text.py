"""Tests for the text on a Contributed Software card.

The page is a Jinja template inside ``contributed-software.rst``. Each test
copies the invented fixture data to a temporary folder, changes the one software
record, renders the page's block with Jinja alone (no Sphinx) and looks at the
resulting reStructuredText. That covers what a card says and in which order,
without a full build. (``test_dataset_card_text.py`` does the same for Datasets.)
"""

import datetime
import shutil

import jinja2
import yaml

from ikp_data.loaders import build_contexts
from tests.test_card_page_templates import FIXTURE_DATA_DIR, jinja_block

TODAY = datetime.date(2027, 3, 15)


def render_card_text(tmp_path, form_data=None, curated=None, **top_level):
    """Render the Software block for the fixture record with the given changes.

    `form_data` and `curated` are merged into those sections of the record;
    `top_level` keys (for example ``country``) replace top-level fields.
    """
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    record_path = next((data_dir / "software").glob("*.yaml"))
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record["form_data"].update(form_data or {})
    record["curated"].update(curated or {})
    record.update(top_level)
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")

    context = build_contexts(data_dir, today=TODAY)["contributed_software"]
    block = jinja_block("contributed-software.rst", "contributed_software")
    return jinja2.Environment().from_string(block).render(**context)


def test_available_status_word_in_table_and_card_badge(tmp_path):
    text = render_card_text(tmp_path)
    assert '<span class="ikp-badge ikp-badge-success">Available</span>' in text
    assert ":bdg-success:`Available`" in text
    assert "Delivered" not in text


def test_in_progress_status_word_in_table_and_card_badge(tmp_path):
    text = render_card_text(tmp_path, form_data={"submitted": False})
    assert '<span class="ikp-badge ikp-badge-muted">In progress</span>' in text
    assert ":bdg-muted:`In progress`" in text
    assert "In Progress" not in text


def test_status_filter_tokens(tmp_path):
    available = render_card_text(tmp_path / "a")
    assert '<option value="status-available">Available</option>' in available
    assert 'data-filter-status="status-available"' in available
    assert 'data-status="available"' in available
    in_progress = render_card_text(tmp_path / "b", form_data={"submitted": False})
    assert 'data-filter-status="status-pending"' in in_progress
    assert 'data-status="pending"' in in_progress
