"""Checks on the card page templates, using the data they are rendered with.

The Telescope Access, Datasets and Software pages are Jinja templates inside
``.. jinja::`` blocks of an .rst file. These tests render each page's block
with the real loader output (the live card data, and the small fixture tree) and
check the structure the page script relies on:

* cards carry no filter data in their class lists (filter data is on the table
  rows and map markers);
* every table row and map marker names an existing card through ``data-card``,
  and every card has a row;
* every filter drop-down's key is a ``data-filter-<key>`` attribute on the rows;
* control ids use the ``ikp-`` prefix (no ``ikt-`` or ``ikc-`` ids), and the script
  does not match class names;
* a same-page "Also see" link renders from the loader's ``kind`` and ``href``.

Only the structure is checked. The text is rendered by Jinja alone, not by
Sphinx, so these tests are quick and need no browser.
"""

import datetime
import functools
import re
import textwrap
from html.parser import HTMLParser
from pathlib import Path

import jinja2
import pytest
import yaml

from ikp_data.loaders import build_contexts

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = REPO_ROOT / "docs" / "contribution-types"
CARDS_JS = REPO_ROOT / "docs" / "_static" / "ikp" / "cards.js"
LIVE_DATA_DIR = PAGES_DIR / "_data"
FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "docs" / "contribution-types" / "_data"
TODAY = datetime.date(2027, 3, 15)

# page file -> (name of the page's jinja context, name of its list of records)
CARD_PAGES = {
    "contributed-telescope.rst": ("contributed_telescopes", "telescopes"),
    "contributed-datasets.rst": ("contributed_datasets", "datasets"),
    "contributed-software.rst": ("contributed_software", "software"),
}

# The only classes a card may carry through `:class-item:`: styling hooks, not filter data.
ALLOWED_CARD_CLASSES = {"ikp-card", "ikp-sw-card"}

DATA_DIRS = [pytest.param(LIVE_DATA_DIR, id="live-data"), pytest.param(FIXTURE_DATA_DIR, id="fixture-data")]


def jinja_block(page, context_name):
    """The body of the page's `.. jinja:: <context_name>` block, dedented."""
    lines = (PAGES_DIR / page).read_text(encoding="utf-8").splitlines()
    start = lines.index(f".. jinja:: {context_name}")
    body = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith(" "):
            break  # the next unindented line ends the block
        body.append(line)
    return textwrap.dedent("\n".join(body))


@functools.lru_cache(maxsize=None)
def contexts_for(data_dir):
    """The loader output for `data_dir`, built once per folder (it is slow)."""
    return build_contexts(data_dir, today=TODAY)


def render_page(page, data_dir):
    """Render the page's block with the loader output for `data_dir`."""
    context_name, _ = CARD_PAGES[page]
    context = contexts_for(data_dir)[context_name]
    return jinja2.Environment().from_string(jinja_block(page, context_name)).render(**context)


class StructureReader(HTMLParser):
    """Collects the attributes of table rows, map markers and filter drop-downs."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.markers = []
        self.select_keys = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "tr" and "data-card" in attributes:
            self.rows.append(attributes)
        elif tag == "circle" and "data-card" in attributes:
            self.markers.append(attributes)
        elif tag == "select" and "data-filter-key" in attributes:
            self.select_keys.append(attributes["data-filter-key"])


def read_structure(rendered):
    reader = StructureReader()
    reader.feed(rendered)
    return reader


def card_anchors(rendered):
    """The ids of the cards: every `.. _label:` line of the rendered block."""
    return re.findall(r"^\s*\.\. _([^:\s]+):\s*$", rendered, flags=re.MULTILINE)


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", CARD_PAGES)
def test_cards_carry_no_filter_tokens_in_their_classes(page, data_dir):
    rendered = render_page(page, data_dir)
    class_lines = re.findall(r"^\s*:class-item:(.*)$", rendered, flags=re.MULTILINE)
    assert class_lines, f"{page} renders no cards"
    for line in class_lines:
        assert set(line.split()) <= ALLOWED_CARD_CLASSES, f"{page}: unexpected card classes {line!r}"


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", CARD_PAGES)
def test_every_row_and_marker_names_an_existing_card(page, data_dir):
    rendered = render_page(page, data_dir)
    anchors = card_anchors(rendered)
    structure = read_structure(rendered)
    row_cards = [row["data-card"] for row in structure.rows]

    assert len(anchors) == len(set(anchors)), f"{page}: a card anchor is used twice"
    assert row_cards, f"{page} renders no table rows"
    # Rows and cards pair up one to one, so a card never lacks a row or the reverse.
    assert sorted(row_cards) == sorted(anchors)
    for marker in structure.markers:
        assert marker["data-card"] in anchors


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", CARD_PAGES)
def test_every_filter_key_is_an_attribute_on_the_rows(page, data_dir):
    structure = read_structure(render_page(page, data_dir))
    assert structure.select_keys, f"{page} has no filter drop-downs"
    for row in structure.rows:
        for key in structure.select_keys:
            assert f"data-filter-{key}" in row, f"{page}: a row lacks data-filter-{key}"
    for marker in structure.markers:
        for key in structure.select_keys:
            assert f"data-filter-{key}" in marker, f"{page}: a marker lacks data-filter-{key}"


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_every_dataset_row_has_a_status_token(data_dir):
    """The Status drop-down filters on the `status` tokens, so every row needs one."""
    rows = read_structure(render_page("contributed-datasets.rst", data_dir)).rows
    assert rows
    for row in rows:
        assert row.get("data-filter-status", "").startswith("status-")


def write_record(data_dir, folder, contribution_id, related):
    """Write the smallest valid dataset or software record into `folder`."""
    record = {
        "contribution_id": contribution_id,
        "title": f"Title of {contribution_id}",
        "last_updated": "2027-03-01",
        "form_data": {},
        "curated": {"related_contribution_ids": related},
    }
    (data_dir / folder).mkdir(parents=True, exist_ok=True)
    (data_dir / folder / f"{contribution_id}.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")


@pytest.mark.parametrize(
    "page, folder, kind, anchor_prefix",
    [
        ("contributed-datasets.rst", "datasets", "dataset", "ds-cid-"),
        ("contributed-software.rst", "software", "software", "sw-cid-"),
    ],
)
def test_a_same_page_also_see_link_renders_its_kind_and_href(tmp_path, page, folder, kind, anchor_prefix):
    write_record(tmp_path, folder, "TST-AAA-S1", ["TST-AAA-S2"])
    write_record(tmp_path, folder, "TST-AAA-S2", [])
    rendered = render_page(page, tmp_path)
    assert f'href="#{anchor_prefix}tst-aaa-s2">Also see: {kind} (TST-AAA-S2)' in rendered


@pytest.mark.parametrize("page", CARD_PAGES)
def test_no_ikt_or_ikc_ids_in_the_templates(page):
    text = (PAGES_DIR / page).read_text(encoding="utf-8")
    assert not re.search(r"\bik[tc]-", text), f"{page} still uses an ikt-/ikc- id"


def test_no_ikt_or_ikc_ids_in_the_script():
    assert not re.search(r"\bik[tc]-", CARDS_JS.read_text(encoding="utf-8"))


def test_the_script_does_not_match_class_names():
    script = CARDS_JS.read_text(encoding="utf-8")
    for needle in ("className", "data-tokens", "'.slug-'", "'.cid-'"):
        assert needle not in script, f"cards.js still mentions {needle!r}"


# ---------------------------------------------------------------------------
# The opportunity banner on the Telescope Access page
# ---------------------------------------------------------------------------

TELESCOPE_PAGE = "contributed-telescope.rst"


def test_the_banner_has_no_inline_style():
    assert "style=" not in jinja_block(TELESCOPE_PAGE, "contributed_opportunities")


def test_the_banner_escapes_its_plain_text_but_not_the_summary():
    block = jinja_block(TELESCOPE_PAGE, "contributed_opportunities")
    for expression in (
        "opp.title",
        "opp.status_line",
        "m.date_text",
        "m.label",
        "link.url",
        "link.label",
        "cid",
    ):
        assert "{{ " + expression + " | e }}" in block, f"{expression} is not escaped"
    # The summary is authored HTML (it may hold <strong>), so it is printed as written.
    assert "{{ opp.summary }}" in block


def test_a_banner_shows_plain_text_as_text_and_the_summary_as_html():
    opportunity = {
        "slug": "x",
        "phase": "in_review",
        "title": "Call <i>A</i> & B",
        "status_line": "Closed & <waiting>",
        "summary": "Open <strong>now</strong>",
        "milestones": [{"label": "Due <soon>", "date_text": "1 Sep 2026", "passed": False}],
        "links": [{"label": "Read <this>", "url": "https://example.org/?a=1&b=2"}],
        "related_contribution_ids": [],
    }
    block = jinja_block(TELESCOPE_PAGE, "contributed_opportunities")
    rendered = jinja2.Environment().from_string(block).render(
        opportunities=[opportunity], cid_to_slugs={}
    )
    assert "Call &lt;i&gt;A&lt;/i&gt; &amp; B" in rendered
    assert "Closed &amp; &lt;waiting&gt;" in rendered
    assert "Due &lt;soon&gt;" in rendered
    assert "Read &lt;this&gt;" in rendered
    assert 'href="https://example.org/?a=1&amp;b=2"' in rendered
    assert "<strong>now</strong>" in rendered
    # The phase class uses a hyphen, and a banner under review is muted.
    assert "ikp-opp-phase-in-review" in rendered
    assert "ikp-opp-card-muted" in rendered
