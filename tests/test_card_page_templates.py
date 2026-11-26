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
* a same-page "Also see" link renders from the loader's ``kind`` and ``href``;
* the "Highlighted" teaser row is absent without a highlight, escapes its text
  and reuses no card id.

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
CARDS_CSS = REPO_ROOT / "docs" / "_static" / "ikp" / "cards.css"
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
    """Collects the attributes of table rows, map markers and filter drop-downs.

    A map marker is any element with the `ikp-map-marker` class token, whatever its
    tag (the script finds markers the same way). The legend's symbols carry only the
    status colour classes, so they are not counted. For each marker the reader also
    keeps its tag, its child <title> texts, and `_tag` / `_titles` as private keys.
    """

    def __init__(self):
        super().__init__()
        self.rows = []
        self.markers = []
        self.select_keys = []
        self._open_marker = None  # the marker whose children are being read
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "tr" and "data-card" in attributes:
            self.rows.append(attributes)
        elif "ikp-map-marker" in attributes.get("class", "").split() and "data-card" in attributes:
            attributes["_tag"] = tag
            attributes["_titles"] = []
            self.markers.append(attributes)
            self._open_marker = attributes
        elif tag == "title" and self._open_marker is not None:
            self._open_marker["_titles"].append("")
            self._in_title = True
        elif tag == "select" and "data-filter-key" in attributes:
            self.select_keys.append(attributes["data-filter-key"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif self._open_marker is not None and tag == self._open_marker["_tag"]:
            self._open_marker = None

    def handle_data(self, data):
        if self._in_title:
            self._open_marker["_titles"][-1] += data


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


# ---------------------------------------------------------------------------
# The "Highlighted" teaser row on the Datasets and Software pages
# ---------------------------------------------------------------------------

TEASER_PAGES = [
    pytest.param("contributed-datasets.rst", "datasets", "ds-cid-", id="datasets"),
    pytest.param("contributed-software.rst", "software", "sw-cid-", id="software"),
]


def write_highlighted_record(data_dir, folder, contribution_id, title, reason, until="2027-04-30"):
    """Write the smallest valid record with a highlight into `folder`."""
    record = {
        "contribution_id": contribution_id,
        "title": title,
        "last_updated": "2027-03-01",
        "form_data": {},
        "curated": {"highlight": {"reason": reason, "until": until}},
    }
    (data_dir / folder).mkdir(parents=True, exist_ok=True)
    (data_dir / folder / f"{contribution_id}.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")


@pytest.mark.parametrize("page, folder, anchor_prefix", TEASER_PAGES)
def test_the_teaser_row_is_absent_without_a_highlight(page, folder, anchor_prefix):
    # The live data has no highlighted record, so the page shows no row at all.
    assert "ikp-teaser" not in render_page(page, LIVE_DATA_DIR)


@pytest.mark.parametrize("page, folder, anchor_prefix", TEASER_PAGES)
def test_the_teaser_row_shows_each_highlight_above_the_filters(page, folder, anchor_prefix):
    rendered = render_page(page, FIXTURE_DATA_DIR)
    assert rendered.count('class="ikp-teaser"') == 1
    assert ">Highlighted<" in rendered
    assert f'class="ikp-teaser-link" href="#{anchor_prefix}tst-fix-' in rendered
    assert rendered.index("ikp-teasers") < rendered.index("ikp-filterbar")


@pytest.mark.parametrize("page, folder, anchor_prefix", TEASER_PAGES)
def test_the_teaser_row_escapes_its_values(tmp_path, page, folder, anchor_prefix):
    write_highlighted_record(tmp_path, folder, "TST-AAA-S1", "<b>Bold</b> & co", "<script>x</script>")
    rendered = render_page(page, tmp_path)
    teaser = rendered[rendered.index('class="ikp-teasers"'):rendered.index("ikp-filterbar")]
    assert "&lt;b&gt;Bold&lt;/b&gt; &amp; co" in teaser
    assert "&lt;script&gt;x&lt;/script&gt;" in teaser
    assert "<b>" not in teaser and "<script>" not in teaser


@pytest.mark.parametrize("page, folder, anchor_prefix", TEASER_PAGES)
def test_a_teaser_adds_no_id_and_links_to_an_existing_card(tmp_path, page, folder, anchor_prefix):
    write_highlighted_record(tmp_path, folder, "TST-AAA-S1", "One", "Newly delivered")
    write_highlighted_record(tmp_path, folder, "TST-AAA-S2", "Two", "Widely used")
    rendered = render_page(page, tmp_path)
    teaser = rendered[rendered.index('class="ikp-teasers"'):rendered.index("ikp-filterbar")]
    # No id attribute inside the row, so no card id (or any other id) is repeated.
    assert "id=" not in teaser
    # Each link names a card that the page does render.
    anchors = re.findall(r'class="ikp-teaser-link" href="#([^"]+)"', teaser)
    assert anchors == [f"{anchor_prefix}tst-aaa-s1", f"{anchor_prefix}tst-aaa-s2"]
    assert set(anchors) <= set(card_anchors(rendered))


def test_the_script_covers_teaser_links_without_filtering_them():
    script = CARDS_JS.read_text(encoding="utf-8")
    # A teaser link to a hidden card clears the filters, like an "Also see" link.
    assert "'.ikp-also-see, .ikp-teaser-link'" in script
    # Both the Datasets and the Software setup wire the teaser links.
    assert script.count("wireTeaserLinks();") == 2
    # The teaser row carries no filter data and is not a table row.
    for page in ("contributed-datasets.rst", "contributed-software.rst"):
        block = jinja_block(page, CARD_PAGES[page][0])
        row = block[block.index("ikp-teasers"):block.index("ikp-filterbar")]
        assert "data-filter-" not in row and "data-card" not in row and "ikp-row" not in row


@pytest.mark.parametrize("page, folder, anchor_prefix", TEASER_PAGES)
def test_a_teaser_with_no_reason_shows_no_badge(tmp_path, page, folder, anchor_prefix):
    write_highlighted_record(tmp_path, folder, "TST-AAA-S1", "One", None)
    rendered = render_page(page, tmp_path)
    teaser = rendered[rendered.index('class="ikp-teasers"'):rendered.index("ikp-filterbar")]
    assert 'class="ikp-teaser-link"' in teaser
    assert "ikp-teaser-reason" not in teaser
    assert "None" not in teaser


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_the_map_markup_has_no_inline_fill_or_stroke_colour(data_dir):
    """The map's colours come from cards.css classes, so dark mode can change them."""
    rendered = render_page("contributed-telescope.rst", data_dir)
    # The map SVG and the legend's SVGs: everything inside the map panel.
    svg = map_panel(rendered)
    # `stroke-width` is a size, not a colour, so only whole `fill=` / `stroke=` attributes count.
    assert not re.search(r'\b(?:fill|stroke)\s*=', svg), "the map SVG has an inline fill or stroke colour"
    assert "ikp-map-bg" in svg and "ikp-map-marker-" in svg  # the classes that replace them are there


# --- The map's label, tooltips and legend ---------------------------------------------

MAP_LABEL = "World map of facility locations; the table below lists every facility"
# status value in the data -> the wording of the table badges (anything else is "Future semester")
STATUS_LABELS = {"available": "Available", "future_semester": "Future semester", "past_opportunity": "Past opportunity"}
# the colour class of each status label
STATUS_CLASSES = {
    "Available": "ikp-map-marker-available",
    "Future semester": "ikp-map-marker-future",
    "Past opportunity": "ikp-map-marker-past",
}


def map_panel(rendered):
    """The markup of the map panel: the map SVG, the legend and their wrapper."""
    start = rendered.index('class="ikp-map-wrap"')
    return rendered[start:rendered.index("<table", start)]


def render_telescopes(telescopes):
    """Render the Telescope Access block with the given list of records."""
    context = dict(contexts_for(LIVE_DATA_DIR)["contributed_telescopes"], telescopes=telescopes)
    return jinja2.Environment().from_string(jinja_block("contributed-telescope.rst", "contributed_telescopes")).render(**context)


def status_label(record):
    return STATUS_LABELS.get(record["status"], "Future semester")


def telescopes_with_markers(data_dir):
    context = contexts_for(data_dir)["contributed_telescopes"]
    return [t for t in context["telescopes"] if t["marker_x"] is not None]


def expected_title(record):
    """The tooltip text: facility, the site when there is one, then the status."""
    place = record["facility"] + (f", {record['site']}" if record.get("site") else "")
    return f"{place}: {status_label(record)}"


def legend_entries(rendered):
    """(text, shape tag, shape attributes, symbol attributes) of each legend item, in order."""
    legend = re.search(r'<ul class="ikp-map-legend"([^>]*)>(.*?)</ul>', rendered, flags=re.S)
    assert legend, "the map has no legend"
    assert 'aria-label="Map key"' in legend.group(1), "the legend is not named 'Map key'"
    assert 'role="list"' in legend.group(1), "the legend lacks role=list (Safari drops list semantics otherwise)"
    entries = []
    for item in re.findall(r"<li>(.*?)</li>", legend.group(2), flags=re.S):
        symbol = re.search(r"<svg ([^>]*)>(.*?)</svg>", item, flags=re.S)
        assert symbol, "a legend item has no symbol"
        text = item.replace(symbol.group(0), "").strip()
        shape = re.search(r"<(circle|rect)\b([^>]*)>", symbol.group(2))
        entries.append((text, shape.group(1), dict(re.findall(r'([\w-]+)="([^"]*)"', shape.group(2))), symbol.group(1)))
    return entries


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_the_map_is_one_labelled_image_that_points_to_the_table(data_dir):
    panel = map_panel(render_page("contributed-telescope.rst", data_dir))
    svg_tag = re.search(r"<svg [^>]*>", panel).group(0)
    assert 'role="img"' in svg_tag
    assert f'aria-label="{MAP_LABEL}"' in svg_tag


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_every_marker_has_one_title_naming_its_facility_site_and_status(data_dir):
    markers = read_structure(render_page("contributed-telescope.rst", data_dir)).markers
    records = {t["slug"]: t for t in telescopes_with_markers(data_dir)}
    assert markers and len(markers) == len(records)
    for marker in markers:
        assert marker["_titles"] == [expected_title(records[marker["data-slug"]])]


def synthetic_record(slug, status, facility="Odd", site=None, marker_x=10, marker_y=20):
    """A minimal telescope record with a marker, for tests that must not depend on the live data."""
    return {
        "slug": slug, "facility": facility, "site": site, "status": status, "marker_x": marker_x,
        "marker_y": marker_y, "filters": {}, "country": None, "instrumentation": [],
    }


def test_a_marker_title_escapes_the_facility_name_and_the_site():
    record = synthetic_record("odd", "available", facility="A<b> & C", site="D<i> & E")
    rendered = render_telescopes([record])
    assert "<title>A&lt;b&gt; &amp; C, D&lt;i&gt; &amp; E: Available</title>" in rendered
    assert "<b>" not in map_panel(rendered) and "<i>" not in map_panel(rendered)
    assert read_structure(rendered).markers[0]["_titles"] == ["A<b> & C, D<i> & E: Available"]


def test_a_marker_title_without_a_site_has_no_stray_comma():
    marker = read_structure(render_telescopes([synthetic_record("odd", "available")])).markers[0]
    assert marker["_titles"] == ["Odd: Available"]


def test_an_unknown_status_is_labelled_future_semester():
    marker = read_structure(render_telescopes([synthetic_record("odd", "something_new")])).markers[0]
    assert marker["_titles"] == ["Odd: Future semester"]
    assert "ikp-map-marker-future" in marker["class"].split()


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_the_legend_lists_the_statuses_in_the_filter_order_with_matching_colours(data_dir):
    rendered = render_page("contributed-telescope.rst", data_dir)
    # The Status drop-down's options, after "All", give the order.
    status_select = re.search(r'<select id="ikp-filter-status".*?</select>', rendered, flags=re.S).group(0)
    filter_order = re.findall(r'<option value="status-[^"]+">([^<]+)</option>', status_select)
    entries = legend_entries(rendered)
    assert [text for text, *_ in entries] == filter_order == list(STATUS_CLASSES)
    for text, _shape, shape_attributes, svg_attributes in entries:
        assert STATUS_CLASSES[text] in shape_attributes["class"].split()
        assert 'aria-hidden="true"' in svg_attributes and 'focusable="false"' in svg_attributes


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_legend_symbols_are_not_markers(data_dir):
    """The script treats `.ikp-map-marker` elements as clickable, filterable markers."""
    rendered = render_page("contributed-telescope.rst", data_dir)
    legend = re.search(r'<ul class="ikp-map-legend"[^>]*>.*?</ul>', rendered, flags=re.S).group(0)
    assert not re.search(r'ikp-map-marker(?![\w-])|data-slug|data-card', legend)
    # And the reader counts the same markers as there are facilities with a position.
    assert len(read_structure(rendered).markers) == len(telescopes_with_markers(data_dir))


# --- The map's shapes: one per status, so colour is not the only cue ---------------------
# Available is a filled circle ("disc"), Future semester a ring (a circle with the outline class),
# Past opportunity a square (a rect).

def shape_of(attributes, tag):
    """The shape's kind: "disc", "ring" or "square", read from its tag and classes."""
    classes = attributes["class"].split()
    if tag == "rect":
        return "square"
    return "ring" if "ikp-map-marker-ring" in classes else "disc"


def marker_centre(marker, kind):
    """The (x, y) a rendered marker is centred on."""
    if kind == "square":
        return (float(marker["x"]) + 5, float(marker["y"]) + 5)
    return (float(marker["cx"]), float(marker["cy"]))


RING_RADIUS = 4.5  # with a 3-wide outline, the ring's outer edge is 6, the same as the dot's radius


def test_each_status_is_drawn_with_its_own_shape_size_title_and_centre():
    """Synthetic records, so the test does not depend on which statuses the live data has.

    The fractional position exercises the square's rounding (444.3 - 5 must print as 439.3).
    """
    position = {"marker_x": 444.3, "marker_y": 170.1}
    records = [
        synthetic_record("a", "available", facility="Alpha", site="Site A", **position),
        synthetic_record("b", "future_semester", facility="Beta", **position),
        synthetic_record("c", "past_opportunity", facility="G<a> & D", site="S&T", **position),
        synthetic_record("d", "something_new", facility="Delta", site="Site D", **position),
    ]
    markers = {m["data-slug"]: m for m in read_structure(render_telescopes(records)).markers}
    # slug -> (tag, ring class present, size attributes, centre, title)
    expected = {
        "a": ("circle", False, {"r": "6"}, "Alpha, Site A: Available"),
        "b": ("circle", True, {"r": str(RING_RADIUS)}, "Beta: Future semester"),
        "c": ("rect", False, {"width": "10", "height": "10"}, "G<a> & D, S&T: Past opportunity"),
        "d": ("circle", True, {"r": str(RING_RADIUS)}, "Delta, Site D: Future semester"),
    }
    assert set(markers) == set(expected)
    for slug, (tag, has_ring_class, size, title) in expected.items():
        marker = markers[slug]
        assert marker["_tag"] == tag
        assert ("ikp-map-marker-ring" in marker["class"].split()) is has_ring_class
        assert {key: marker[key] for key in size} == size
        assert marker_centre(marker, shape_of(marker, tag)) == pytest.approx((444.3, 170.1), abs=1e-9)
        assert marker["_titles"] == [title]
    # The square's corner is printed without float noise.
    assert (markers["c"]["x"], markers["c"]["y"]) == ("439.3", "165.1")


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_every_rendered_marker_shape_matches_its_status_and_centre(data_dir):
    """Whatever statuses the data has, each marker's shape and colour match its record."""
    records = {t["slug"]: t for t in telescopes_with_markers(data_dir)}
    markers = read_structure(render_page("contributed-telescope.rst", data_dir)).markers
    expected_shape = {"available": "disc", "future_semester": "ring", "past_opportunity": "square"}
    for marker in markers:
        record = records[marker["data-slug"]]
        kind = shape_of(marker, marker["_tag"])
        assert kind == expected_shape.get(record["status"], "ring")
        assert STATUS_CLASSES[status_label(record)] in marker["class"].split()
        assert marker_centre(marker, kind) == pytest.approx((record["marker_x"], record["marker_y"]), abs=0.01)


@pytest.mark.parametrize("data_dir", DATA_DIRS)
def test_legend_symbols_use_the_same_shapes_as_the_markers(data_dir):
    entries = legend_entries(render_page("contributed-telescope.rst", data_dir))
    kinds = {text: shape_of({"class": attrs["class"]}, tag) for text, tag, attrs, _ in entries}
    assert kinds == {"Available": "disc", "Future semester": "ring", "Past opportunity": "square"}


def test_the_ring_is_an_outline_and_a_hollow_middle_still_takes_the_pointer():
    css = CARDS_CSS.read_text(encoding="utf-8")
    ring_rule = re.search(r"\.ikp-map-marker-ring\.ikp-map-marker-future\s*\{([^}]*)\}", css).group(1)
    assert "fill: none" in ring_rule
    assert "stroke: var(--ikp-map-marker-future)" in ring_rule
    assert "pointer-events: all" in ring_rule
    assert "stroke-width: 3" in ring_rule
    # The hover rule must exist, or the ring's own stroke would cancel the hover outline.
    hover_rule = re.search(r"\.ikp-map-marker\.ikp-map-marker-ring:hover\s*\{([^}]*)\}", css).group(1)
    assert "stroke: var(--ikp-map-marker-hover)" in hover_rule


# page file -> (id of the search box, text of its visually hidden label)
SEARCH_LABELS = {
    "contributed-telescope.rst": ("ikp-search", "Search facilities"),
    "contributed-datasets.rst": ("ikp-search", "Search datasets"),
    "contributed-software.rst": ("ikp-sw-search", "Search software"),
}


@pytest.mark.parametrize("page", SEARCH_LABELS)
def test_each_search_box_has_a_visually_hidden_label(page):
    """The placeholder is not a name; a label gives the box one (WCAG 4.1.2, 3.3.2)."""
    input_id, label_text = SEARCH_LABELS[page]
    rendered = render_page(page, FIXTURE_DATA_DIR)
    assert f'<label for="{input_id}" class="ikp-visually-hidden">{label_text}</label>' in rendered
    assert f'<input type="text" id="{input_id}"' in rendered  # still type="text"


# page file -> (noun in the count line, the page's "no results" text)
RESULT_COUNT_TEXT = {
    "contributed-telescope.rst": ("facilities", "No facilities match the filters"),
    "contributed-datasets.rst": ("datasets", "No datasets match the filters"),
    "contributed-software.rst": ("software contributions", "No software contributions match the filters"),
}


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", RESULT_COUNT_TEXT)
def test_the_template_renders_the_full_count_for_use_without_js(page, data_dir):
    noun, _ = RESULT_COUNT_TEXT[page]
    rendered = render_page(page, data_dir)
    total = len(read_structure(rendered).rows)
    assert total > 0
    assert f'<p class="ikp-result-count">Showing {total} of {total} {noun}</p>' in rendered
    assert rendered.count("ikp-result-count") == 1


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", RESULT_COUNT_TEXT)
def test_only_the_hidden_announcer_is_a_status_region_and_it_starts_empty(page, data_dir):
    rendered = render_page(page, data_dir)
    # The visible count is plain text; the hidden announcer is the one status region.
    assert rendered.count('role="status"') == 1
    assert '<p class="ikp-visually-hidden ikp-status" role="status"></p>' in rendered


@pytest.mark.parametrize("page", RESULT_COUNT_TEXT)
def test_the_script_knows_each_pages_noun_and_zero_results_text(page):
    noun, none_text = RESULT_COUNT_TEXT[page]
    script = CARDS_JS.read_text(encoding="utf-8")
    # The template renders the noun and the script rewrites it; they must agree.
    assert f"noun: '{noun}'" in script
    assert none_text in script


# The sortable headers: each holds a real button (so the keyboard and screen readers can use it) and
# an empty, hidden arrow that the script fills after a sort (WCAG 2.1.1, 4.1.2).
SORT_HEADER = re.compile(r"<th\b([^>]*\bdata-sort=[^>]*)>(.*?)</th>", flags=re.DOTALL)
SORT_BUTTON_CONTENT = re.compile(
    r'<button type="button" class="ikp-sort-btn">[^<]+<span class="ikp-sort-arrow" aria-hidden="true"></span></button>'
)
SORTABLE_COLUMN_COUNTS = {
    "contributed-telescope.rst": 5,
    "contributed-datasets.rst": 6,
    "contributed-software.rst": 5,
}


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", SORTABLE_COLUMN_COUNTS)
def test_each_sortable_header_is_a_column_header_holding_one_button_and_an_empty_arrow(page, data_dir):
    rendered = render_page(page, data_dir)
    headers = SORT_HEADER.findall(rendered)
    assert len(headers) == SORTABLE_COLUMN_COUNTS[page]
    for attributes, content in headers:
        assert 'scope="col"' in attributes, f"{page}: a sortable header lacks scope=col"
        assert SORT_BUTTON_CONTENT.fullmatch(content), f"{page}: unexpected header content {content!r}"
    # No header is marked as sorted at load; the script sets this after a sort.
    assert "aria-sort=" not in rendered


# The "Show more" toggles: each button names the region it opens (`aria-controls`), starts collapsed and
# hidden (the script shows it), and keeps its glyphs out of the accessible name (WCAG 4.1.2).
TOGGLE_PAGES = {
    # page -> (button class, region id suffix)
    "contributed-software.rst": ("ikp-expand-btn", "-desc"),
    "contributed-datasets.rst": ("ikp-more-btn", "-more"),
}
TOGGLE_BUTTON = re.compile(r"<button\b([^>]*)>(.*?)</button>", flags=re.DOTALL)
HIDDEN_GLYPH_SPAN = re.compile(r'<span aria-hidden="true">[^<]*</span>')
TOGGLE_GLYPHS = ["▾", "&#9662;", "▴", "&#9652;", "→", "&rarr;"]


def toggle_buttons(rendered, button_class):
    """The attribute text of every toggle button of `button_class` in the rendered page."""
    return [
        attributes for attributes, _ in TOGGLE_BUTTON.findall(rendered)
        if f'class="{button_class}"' in attributes
    ]


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", TOGGLE_PAGES)
def test_each_toggle_button_is_collapsed_hidden_and_names_one_region(page, data_dir):
    button_class, suffix = TOGGLE_PAGES[page]
    rendered = render_page(page, data_dir)
    buttons = toggle_buttons(rendered, button_class)
    assert buttons, f"{page}: no toggle buttons found"
    controlled = []
    for attributes in buttons:
        assert 'type="button"' in attributes
        assert re.search(r"\bhidden\b", attributes), f"{page}: a toggle button is not hidden at load"
        assert 'aria-expanded="false"' in attributes
        controls = re.search(r'aria-controls="([^"]+)"', attributes)
        assert controls is not None, f"{page}: a toggle button has no aria-controls"
        region_id = controls.group(1)
        assert region_id.endswith(suffix)
        controlled.append(region_id)
        # Software renders the region as raw HTML; Datasets names the container directive.
        region_markers = [f'id="{region_id}"', f":name: {region_id}"]
        assert sum(rendered.count(marker) for marker in region_markers) == 1, (
            f"{page}: {region_id} is not defined exactly once"
        )
    assert len(controlled) == len(set(controlled)), f"{page}: two buttons control the same region"


@pytest.mark.parametrize("data_dir", DATA_DIRS)
@pytest.mark.parametrize("page", ["contributed-software.rst", "contributed-datasets.rst"])
def test_toggle_and_also_see_glyphs_appear_only_inside_aria_hidden_spans(page, data_dir):
    rendered = render_page(page, data_dir)
    without_hidden_spans = HIDDEN_GLYPH_SPAN.sub("", rendered)
    for glyph in TOGGLE_GLYPHS:
        assert glyph not in without_hidden_spans, f"{page}: {glyph!r} is outside an aria-hidden span"


def test_the_script_finds_each_toggle_region_through_aria_controls():
    script = CARDS_JS.read_text(encoding="utf-8")
    assert "previousElementSibling" not in script
    assert "aria-controls" in script


def css_rules_mentioning(css, needle):
    """The selector text of every CSS rule whose declarations contain `needle`.

    Simple approach: split the file on "}" so each chunk ends with one rule, "selector { declarations",
    and keep the text between the last two "{". The first rule inside an "@media (...) {" block
    arrives as "@media (...) { selector { declarations", so taking the last "{" keeps its own
    selector rather than the media query.
    """
    selectors = []
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        before, declarations = chunk.rsplit("{", 1)
        selector = before.rsplit("{", 1)[-1]
        if needle in declarations:
            # Drop any comment text that sits in front of the selector.
            selectors.append(selector.split("*/")[-1].strip())
    return selectors


def test_the_collapsing_css_applies_only_once_the_script_has_run():
    """Without JavaScript the fields and descriptions must show in full and no button may appear."""
    css = CARDS_CSS.read_text(encoding="utf-8")

    hiding = [s for s in css_rules_mentioning(css, "display: none") if ".ikp-more-fields" in s]
    assert hiding, "no rule hides .ikp-more-fields"
    for selector in hiding:
        assert ".ikp-collapsible" in selector, f"{selector!r} hides the fields without the script"

    clamping = [s for s in css_rules_mentioning(css, "-webkit-line-clamp") if ".ikp-desc" in s]
    assert clamping, "no rule clamps .ikp-desc"
    for selector in clamping:
        assert ".ikp-collapsible" in selector, f"{selector!r} clamps the text without the script"

    fading = [s for s in css_rules_mentioning(css, "mask-image") if ".ikp-desc" in s]
    assert fading, "no rule masks .ikp-desc"
    for selector in fading:
        assert ".ikp-faded" in selector, f"{selector!r} masks the text without the script"

    # The buttons stay hidden until the script shows them.
    hidden_rules = css_rules_mentioning(css, "display: none")
    for button_class in (".ikp-more-btn", ".ikp-expand-btn"):
        assert any(f"{button_class}[hidden]" in s for s in hidden_rules), f"no [hidden] rule for {button_class}"
