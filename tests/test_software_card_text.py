"""Tests for the text on a Contributed Software card.

The page is a Jinja template inside ``contributed-software.rst``. Each test
copies the invented fixture data to a temporary folder, changes the one software
record, renders the page's block with Jinja alone (no Sphinx) and looks at the
resulting reStructuredText. That covers what a card says and in which order,
without a full build. (``test_dataset_card_text.py`` does the same for Datasets.)
"""

import datetime
import html
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


def test_card_header_spells_out_uk_and_leaves_other_countries(tmp_path):
    uk = render_card_text(tmp_path / "uk", country="UK")
    assert "TST-FIX-S3 - United Kingdom\n" in uk
    other = render_card_text(tmp_path / "other", country="Examplia")
    assert "TST-FIX-S3 - Examplia\n" in other


def test_card_header_has_no_country_part_when_the_record_has_none(tmp_path):
    text = render_card_text(tmp_path, country=None)
    header = [line.strip() for line in text.splitlines() if line.strip().startswith("TST-FIX-S3")]
    assert header == ["TST-FIX-S3"]


def test_loader_adds_display_country_without_changing_the_stored_country(tmp_path):
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    record_path = next((data_dir / "software").glob("*.yaml"))
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record["country"] = "UK"
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    software = build_contexts(data_dir, today=TODAY)["contributed_software"]["software"][0]
    assert software["country"] == "UK"
    assert software["display_country"] == "United Kingdom"


def test_category_row_shows_the_category_or_tbd(tmp_path):
    text = render_card_text(tmp_path / "a", form_data={"category": "Non-directable SW dev"})
    assert "**Category:** Non-directable SW dev" in text
    for index, empty in enumerate((None, "")):
        blank = render_card_text(tmp_path / f"b{index}", form_data={"category": empty})
        assert "**Category:** TBD" in blank


def test_category_row_follows_the_recipients(tmp_path):
    text = render_card_text(tmp_path)
    assert text.index("**Additional recipients:**") < text.index("**Category:**")


# --- Support row -----------------------------------------------------------


def support_line(text):
    """The card's "**Support:** ..." line from rendered text, without indentation."""
    for line in text.splitlines():
        if line.strip().startswith("**Support:**"):
            return line.strip()
    return None


def test_support_row_follows_documentation_and_is_hidden_when_empty(tmp_path):
    text = render_card_text(tmp_path / "a", form_data={"support": "Use the forum."})
    assert "**Support:** Use the forum." in text
    assert text.index("**Documentation:**") < text.index("**Support:**")
    assert support_line(render_card_text(tmp_path / "b", form_data={"support": None})) is None
    assert support_line(render_card_text(tmp_path / "c", form_data={"support": ""})) is None


def test_email_addresses_in_the_support_answer_become_mailto_links(tmp_path):
    answer = "Write to a.person@example.org or use the forum."
    line = support_line(render_card_text(tmp_path, form_data={"support": answer}))
    document, warnings = parse_rst(line)
    assert warnings == ""
    assert [r["refuri"] for r in document.findall(docutils.nodes.reference)] == [
        "mailto:a.person@example.org"
    ]


def test_every_live_support_answer_renders_without_rst_warnings(tmp_path):
    """The real answers, including emails inside "[ ... ]", must parse cleanly."""
    live_dir = REPO_ROOT / "docs" / "contribution-types" / "_data" / "software"
    checked = 0
    for index, path in enumerate(sorted(live_dir.glob("*.yaml"))):
        answer = (yaml.safe_load(path.read_text(encoding="utf-8")).get("form_data") or {}).get("support")
        if not answer:
            continue
        line = support_line(render_card_text(tmp_path / str(index), form_data={"support": answer}))
        _, warnings = parse_rst(line)
        assert warnings == "", f"{path.name}: {warnings}"
        checked += 1
    assert checked >= 1


def test_bracketed_emails_still_link_without_the_brackets(tmp_path):
    answer = "Contact us by email at [ a.one@example.org and b.two@example.org]. Thanks."
    line = support_line(render_card_text(tmp_path, form_data={"support": answer}))
    document, warnings = parse_rst(line)
    assert warnings == ""
    assert [r["refuri"] for r in document.findall(docutils.nodes.reference)] == [
        "mailto:a.one@example.org",
        "mailto:b.two@example.org",
    ]


# --- Layout: short rows first, then the description ------------------------


def test_short_rows_come_before_the_description_in_page_order(tmp_path):
    text = render_card_text(
        tmp_path,
        form_data={"version": "1.0", "support": "Ask on the forum."},
    )
    markers = [
        "**Primary recipient:**",
        "**Category:**",
        "**Version:**",
        "**Software:**",
        "**Start (approx.):**",
        "**Links:**",
        "**Documentation:**",
        "**Support:**",
        'class="ikp-desc"',
        'class="ikp-expand-btn"',
        'class="ikp-also-see"',
    ]
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)


def test_description_toggle_labels_have_arrows(tmp_path):
    text = render_card_text(tmp_path)
    # &#9662; is the down-pointing small triangle and &#9652; the up-pointing one.
    assert 'data-expand-label="Read full description &#9662;"' in text
    assert 'data-collapse-label="Show less &#9652;"' in text
    assert ">Read full description &#9662;</button>" in text


def test_description_toggle_does_not_say_show_more(tmp_path):
    assert ">Show more<" not in render_card_text(tmp_path)


# --- Description escaping ---------------------------------------------------


def description_html_for(tmp_path, description):
    """The `description_html` the loader builds for the fixture record."""
    data_dir = tmp_path / "_data"
    shutil.copytree(FIXTURE_DATA_DIR, data_dir)
    record_path = next((data_dir / "software").glob("*.yaml"))
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record["form_data"]["activity_description"] = description
    record_path.write_text(yaml.safe_dump(record), encoding="utf-8")
    software = build_contexts(data_dir, today=TODAY)["contributed_software"]["software"][0]
    return software["description_html"]


def test_markup_in_a_description_is_shown_as_text(tmp_path):
    escaped = description_html_for(tmp_path, "<script>alert(1)</script> and a < b")
    assert "<script>" not in escaped
    assert escaped == "&lt;script&gt;alert(1)&lt;/script&gt; and a &lt; b"


def test_an_ampersand_is_escaped_once(tmp_path):
    assert description_html_for(tmp_path, "Stars & galaxies") == "Stars &amp; galaxies"


def test_an_existing_entity_is_not_escaped_twice(tmp_path):
    """A literal "&amp;" in the data must still show as one "&", not "&amp;"."""
    escaped = description_html_for(tmp_path, "Stars &amp; galaxies")
    assert escaped == "Stars &amp; galaxies"
    assert html.unescape(escaped) == "Stars & galaxies"


def test_an_empty_description_shows_tbd(tmp_path):
    assert description_html_for(tmp_path / "a", None) == "TBD"
    assert description_html_for(tmp_path / "b", "") == "TBD"


def test_the_card_shows_the_escaped_description(tmp_path):
    text = render_card_text(tmp_path, form_data={"activity_description": "x <script> y"})
    assert '<div class="ikp-desc">x &lt;script&gt; y</div>' in text
    assert "<script>" not in text.replace('<script type="application/json"', "")


def test_no_live_description_can_start_a_tag():
    """No live answer may put a raw "<" into the card's HTML block."""
    live_data_dir = REPO_ROOT / "docs" / "contribution-types" / "_data"
    records = build_contexts(live_data_dir, today=TODAY)["contributed_software"]["software"]
    assert records
    for software in records:
        assert "<" not in software["description_html"], software["contribution_id"]
