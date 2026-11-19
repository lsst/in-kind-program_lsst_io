"""Tests for the text on a Contributed Software card.

The page is a Jinja template inside ``contributed-software.rst``. Each test
copies the invented fixture data to a temporary folder, changes the one software
record, renders the page's block with Jinja alone (no Sphinx) and looks at the
resulting reStructuredText. That covers what a card says and in which order,
without a full build. (``test_dataset_card_text.py`` does the same for Datasets.)
"""

import datetime
import io
import shutil
from pathlib import Path

import docutils.core
import docutils.nodes
import jinja2
import yaml

from ikp_data.loaders import build_contexts
from tests.test_card_page_templates import FIXTURE_DATA_DIR, jinja_block

TODAY = datetime.date(2027, 3, 15)
REPO_ROOT = Path(__file__).resolve().parent.parent


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


def test_version_comes_from_the_form_on_available_cards(tmp_path):
    text = render_card_text(tmp_path, form_data={"version": "0.1.2"})
    assert "**Version:** 0.1.2" in text


def test_curated_version_overrides_the_form_version(tmp_path):
    text = render_card_text(
        tmp_path, form_data={"version": "long messy form answer"}, curated={"version": "v1.0.0"}
    )
    assert "**Version:** v1.0.0" in text
    assert "long messy form answer" not in text


def test_version_row_is_hidden_when_there_is_no_version(tmp_path):
    assert "**Version:**" not in render_card_text(tmp_path / "a", form_data={"version": None})
    assert "**Version:**" not in render_card_text(tmp_path / "b", form_data={"version": ""})


def test_version_is_not_shown_on_in_progress_cards(tmp_path):
    text = render_card_text(
        tmp_path, form_data={"submitted": False, "version": "0.1.2"}, curated={"version": "v1"}
    )
    assert "**Version:**" not in text


def test_version_is_on_the_card_only_not_in_the_table(tmp_path):
    text = render_card_text(tmp_path, form_data={"version": "0.1.2"})
    # The only line that mentions the version is the card's Version row.
    lines_with_version = [line.strip() for line in text.splitlines() if "0.1.2" in line]
    assert lines_with_version == ["**Version:** 0.1.2"]


def parse_rst(source):
    """Parse reStructuredText with docutils; return (document, warnings text)."""
    warnings = io.StringIO()
    document = docutils.core.publish_doctree(
        source, settings_overrides={"warning_stream": warnings, "report_level": 1}
    )
    return document, warnings.getvalue()


def test_every_live_version_renders_without_rst_warnings():
    """A future form sync that brings in reStructuredText markup must fail here,
    not reach the page. Each live display_version is parsed as the card's row."""
    live_data_dir = REPO_ROOT / "docs" / "contribution-types" / "_data"
    records = build_contexts(live_data_dir, today=TODAY)["contributed_software"]["software"]
    versions = {r["contribution_id"]: r["display_version"] for r in records if r["display_version"]}
    assert versions, "expected at least one live version"
    for contribution_id, version in versions.items():
        _, warnings = parse_rst(f"**Version:** {version}")
        assert warnings == "", f"{contribution_id}: {warnings}"
