"""Helpers shared by the card loaders (and by ``ikp_data.checks``).

Why this file exists
--------------------
The five loaders in ``ikp_data.loaders`` each turn raw YAML records into the
dictionaries the page templates render. They need the same small tools, so those
tools live here once instead of being copied into every loader (and into the
cross-record checks):

* text helpers: ``slugify``, ``option_pairs`` and ``normalize_strings``;
* ``largest_metre_value``: the number a telescope table sorts its Aperture
  column by;
* ``display_country``: the spelling of a country shown on a card header;
* ``search_index_to_json``: dumps a page's search index so it is safe to embed in a
  ``<script>`` block;
* cross-page lookups: ``collect_cross_page_targets`` and ``resolve_related_titles``
  (how a card labels its "Also see" links to another page);
* the telescope fields that sibling records must agree on;
* map geometry: projecting latitude/longitude onto the world-outline SVG and
  nudging markers that would overlap;
* ``require_field``: reads a required field, or raises an error naming the file;
* ``sort_cards``: the order of the cards and table rows on the Datasets and
  Software pages;
* ``active_highlights``: the short list behind the "Highlighted" teaser row on
  those two pages;
* ``record_last_updated``: reads a card's explicit ``last_updated`` date;
* ``parse_date``: reads a date that may be a date object or an ISO string;
* ``format_date``: writes a date for readers, as "30 Sep 2026".

Nothing in this module reads the clock, runs git, or locates files by itself:
callers pass in the dates and paths they want used.
"""

import datetime
import json
import math
import re
from pathlib import Path

import yaml

# Telescope fields that must be authored identically across sibling records that
# are the same facility at several sites. Used by ``ikp_data.checks``, which
# reports a validation warning when they drift apart.
SIBLING_CONSISTENCY_FIELDS = (
    "summary",
    "time_available",
    "duration",
    "status",
    "tac_process",
)


def slugify(value):
    """Lowercase, and turn each run of other characters into one "-"."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


# A size in metres: a number directly followed by "m" (an optional space is
# allowed, and "mm" or "meters" do not count). A number with no "m" after it,
# such as the "2" in "2 x 8.4m", is a count, not a size.
_METRE_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*m(?![A-Za-z])")


def largest_metre_value(text):
    """The largest size in metres named in free text, as a float, or None.

    "2 x 8.4m" gives 8.4, "1.5m / 1.0m" gives 1.5 and "1.9m-1.0m" gives 1.9.
    Text with no size (or no text) gives None, so the table can sort such rows last.
    Only "digits, optional point, digits" is read: ".5m" gives 5 and a decimal
    comma ("8,4m") gives 4. Neither spelling is used in the data.
    """
    if not text:
        return None
    values = [float(number) for number in _METRE_VALUE_RE.findall(text)]
    return max(values) if values else None


# Country names that the data spells in a short form but a card header should
# spell out. Anything not listed here is shown exactly as it is stored.
COUNTRY_DISPLAY_NAMES = {
    "UK": "United Kingdom",
}


def display_country(country):
    """The country as a card header should show it.

    The records spell some countries two ways (for example "UK" and "United
    Kingdom"). Mapping at display time keeps the data files untouched, so a
    form sync cannot undo it. A country with no entry in
    ``COUNTRY_DISPLAY_NAMES`` (or no country at all) is returned unchanged.
    """
    return COUNTRY_DISPLAY_NAMES.get(country, country)


def option_pairs(values):
    """Sorted ``(label, slug)`` pairs for a filter drop-down's options.

    The page templates build each ``<option value="...">`` from the slug and show
    the label. Computing the pairs here keeps the Jinja contexts plain data (no
    functions), which Sphinx needs in order to cache its configuration.
    """
    return [(label, slugify(label)) for label in sorted(values)]


def parse_date(value):
    """A ``datetime.date`` from a date, a datetime or an ISO "YYYY-MM-DD" string.

    YAML gives us a date object for an unquoted date and a string for a quoted
    one, so every loader needs to accept both. Returns None for anything else
    (including a string that is not a valid date): the schema checks in
    ``ikp_data.validate`` are where bad dates are reported, so the loaders just
    treat an unreadable date as absent.
    """
    # datetime is a subclass of date, so it must be tested first.
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None
    return None


# English month abbreviations, written out so the result never depends on the
# machine's locale (``strftime("%b")`` follows the locale).
_MONTH_ABBREVIATIONS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def format_date(value):
    """A date written for readers: "30 Sep 2026" (day, month, four-digit year).

    The day has no leading zero ("1 Sep 2026") and the month is the English
    three-letter abbreviation. `value` may be anything ``parse_date`` accepts.
    Returns None when `value` is not a readable date, so the caller can decide
    what to show instead.
    """
    date = parse_date(value)
    if date is None:
        return None
    return f"{date.day} {_MONTH_ABBREVIATIONS[date.month - 1]} {date.year:04d}"


def normalize_strings(obj):
    """Recursively collapse embedded/trailing newlines and extra whitespace.

    YAML block scalars (`>` or `|`) can leave a trailing newline, or authors
    may wrap long strings across lines. Any such string ends up substituted
    inline into HTML attributes and RST directive arguments by the Jinja
    template; a stray unindented newline there breaks the surrounding
    `.. raw:: html` block (or the directive line), so every string value is
    normalized to a single line with collapsed whitespace at load time.
    """
    if isinstance(obj, str):
        return " ".join(obj.split())
    if isinstance(obj, list):
        return [normalize_strings(v) for v in obj]
    if isinstance(obj, dict):
        return {k: normalize_strings(v) for k, v in obj.items()}
    return obj


def search_index_to_json(search_index):
    """Return `search_index` as JSON text that is safe inside a ``<script>`` block.

    Why: each card page embeds its search index in
    ``<script type="application/json" data-ikp="search-index">``. The index is
    built from form responses, so a value containing ``</script`` would end that
    block early and let the rest of the value be read as page HTML. Writing every
    ``<`` as the JSON escape ``\\u003c`` prevents that. ``JSON.parse`` (and
    ``json.loads``) turn the escape back into ``<``, so the strings the page
    script sees are identical.
    """
    return json.dumps(search_index).replace("<", "\\u003c")


def require_field(record, key, path):
    """The value of a field the schema requires, or a ValueError naming the file.

    Without this, a record that lacks the field would fail deep inside the build
    with a bare KeyError (or TypeError, for an explicit ``null``) that does not
    say which file is at fault.
    """
    value = record.get(key)
    if value is None:
        raise ValueError(
            f"{path}: missing required field '{key}'; "
            "run `tox run -e validate` to see all problems"
        )
    return value


def record_last_updated(record, path):
    """The "Updated" date shown on a dataset/software card.

    Each card's YAML carries an explicit, quoted `last_updated: 'YYYY-MM-DD'`
    (ADR 0007), so the date means "content last changed" and is not disturbed
    by maintenance commits. The schema requires the field, so a missing value
    is an authoring error: we raise an error naming the file instead of
    guessing a date. The value is returned as a string, so templates and
    sorting are unchanged.
    """
    explicit = record.get("last_updated")
    if not explicit:
        raise ValueError(
            f"{path}: missing required `last_updated` (quoted 'YYYY-MM-DD'); "
            "see ADR 0007. Run `tox run -e validate` for details."
        )
    return str(explicit)


def _natural_key(text):
    """A sort key that compares the digit runs in `text` as numbers.

    "ITA-INA-S2" sorts before "ITA-INA-S10", as a reader expects, where plain
    text order would put "S10" first. The key splits the text into pieces, such
    as ["ITA-INA-S", 2, ""], and a split always alternates text and number, so
    two keys compare piece by piece without ever comparing text with a number.
    """
    return [int(piece) if piece.isdigit() else piece for piece in re.split(r"(\d+)", text)]


def sort_cards(records):
    """Return `records` in page order: Available first, then the most recently
    updated, then by contribution ID (A to Z, with numbers in order: S2 before S10) so
    equal dates keep a stable order.

    The cards and the table rows are built from the same list, so they share
    this order. `last_updated` is an ISO date string, so text order is date
    order. The loaders always give a record a date (`record_last_updated` raises
    without one), but a record with no date would come last in its group.
    """
    # Python's sort is stable: sorting by the least important key first and the
    # most important key last gives the combined order. The date key needs a
    # reversed sort, which is why this is three passes and not one tuple key.
    ordered = sorted(records, key=lambda r: _natural_key(r.get("contribution_id") or ""))
    ordered.sort(key=lambda r: r.get("last_updated") or "", reverse=True)
    ordered.sort(key=lambda r: r.get("status") != "available")
    return ordered


# The most teasers the "Highlighted" row shows on one page.
MAX_HIGHLIGHTS = 3


def active_highlights(records, today):
    """The teasers for the "Highlighted" row: one dictionary per active highlight.

    A record is highlighted when ``curated.highlight`` has a readable ``until``
    date that is not before `today`. The ``until`` day itself still counts, as
    ``visible_until`` does for a banner. The list is ordered soonest-expiring
    first, with ties broken by contribution ID (numbers in order, as
    ``sort_cards`` does), and holds at most ``MAX_HIGHLIGHTS`` entries. Each
    entry has the card's ``title``, the badge ``reason`` and the card's
    ``anchor``, which the template uses as the link target.

    `records` are the loaders' records, which already carry an ``anchor``.
    A highlight with no readable date, or one that is not a mapping, is
    skipped: ``ikp_data.validate`` is where a bad one is reported.
    """
    candidates = []
    for record in records:
        highlight = (record.get("curated") or {}).get("highlight")
        # A highlight that is not a mapping is malformed: treat it as absent.
        # (``ikp_data.validate`` reports it.)
        if not isinstance(highlight, dict):
            continue
        until = parse_date(highlight.get("until"))
        if until is None or until < today:
            continue
        candidates.append((until, record, highlight))
    candidates.sort(key=lambda c: (c[0], _natural_key(c[1].get("contribution_id") or "")))
    return [
        {
            "title": record.get("title", ""),
            "reason": highlight.get("reason") or "",
            "anchor": record["anchor"],
        }
        for _, record, highlight in candidates[:MAX_HIGHLIGHTS]
    ]


def collect_cross_page_targets(data_dir, subdir_name, anchor_for):
    """contribution_id -> {"title", "anchors"} lookup for a sibling _data folder.

    Used to label a page's "Also see" cross-links to another page, and to point
    each link at the right card, without needing that other page's full loader
    context.

    * ``title``: the record's title (or facility, or the ID itself).
    * ``anchors``: the in-page anchor of every card with this contribution ID,
      without the leading "#". It is a list because the Telescopes page can have
      several sibling cards (for example KMTNet's three sites) sharing one ID.

    ``contribution_id`` may be a scalar or, on the Telescopes page, a list.
    ``data_dir`` is the `_data` folder; ``subdir_name`` is the record type's
    folder inside it (for example "software"). ``anchor_for(path, cid)`` returns
    the anchor the target page gives the card in ``path`` for ``cid``. It is a
    parameter because each page names its anchors differently.
    """
    subdir = data_dir / subdir_name
    out = {}
    if not subdir.exists():
        return out
    for path in sorted(subdir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        cid = record.get("contribution_id")
        cids = cid if isinstance(cid, list) else [cid]
        for c in cids:
            if not c:
                continue
            target = out.setdefault(c, {"title": None, "anchors": []})
            # With siblings, the last file's title wins (as before this lookup
            # kept anchors); sibling cards share a facility name anyway.
            target["title"] = record.get("title") or record.get("facility") or c
            target["anchors"].append(anchor_for(path, c))
    return out


# Anchor builders for collect_cross_page_targets. Each must match the label the
# target page's template gives its cards:
#   datasets.rst   ".. _ds-cid-<cid slug>:"
#   software.rst   ".. _sw-cid-<cid slug>:"
def dataset_anchor(path, cid):
    return f"ds-cid-{slugify(cid)}"


def software_anchor(path, cid):
    return f"sw-cid-{slugify(cid)}"


def resolve_related_titles(related_ids, *page_lookups, current_page=None, own_id=None):
    """Label and locate each related contribution ID for a card's "Also see" links.

    page_lookups is a sequence of (page_html_filename, targets, kind) triples:
    ``targets`` comes from ``collect_cross_page_targets`` and ``kind`` is the word
    the link uses for that record type ("dataset" or "software"). They are checked
    in order, and the first page that has the ID wins. A caller lists the OTHER
    page first: an ID that names both a dataset and a software record (one
    contribution that delivers both) links across to the other page, and only an ID
    found nowhere else links within the page.

    ``current_page`` is the filename of the page the card is on. A link to a card on
    that page is just ``#anchor``; a link to another page is ``page.html#anchor``.
    ``own_id`` is the card's own contribution ID: a card never links to itself, so
    that ID is skipped when it would resolve to the card's own page. (An ID that
    names only the card itself is reported by ``ikp_data.checks``, so validation
    catches it before it silently produces no link.)

    Each returned dict has:
    * ``contribution_id`` and ``title``: the related ID and its record's title;
    * ``kind``: "dataset" or "software" (the target's type), or None if the ID
      resolved to nothing;
    * ``href``: the link target, or None if the ID resolved to nothing;
    * ``anchor``: the anchor on the target page (the first card when several
      siblings share the ID);
    * ``anchors``: every sibling's anchor, for templates that want them all.
    """
    resolved = []
    for rid in related_ids or []:
        title = None
        kind = None
        href = None
        anchors = []
        for page_html, targets, target_kind in page_lookups:
            if page_html == current_page and rid == own_id:
                continue
            if rid in targets:
                title = targets[rid]["title"]
                kind = target_kind
                anchors = list(targets[rid]["anchors"])
                prefix = "" if page_html == current_page else page_html
                href = f"{prefix}#{anchors[0]}" if anchors else None
                break
        resolved.append({
            "contribution_id": rid,
            "title": title or rid,
            "kind": kind,
            "href": href,
            "anchor": anchors[0] if anchors else None,
            "anchors": anchors,
        })
    return resolved


def to_marker_xy(latitude, longitude):
    """Equirectangular projection onto a 0-1000 x 0-500 canvas (matches the
    world-outline SVG's viewBox in _static/). (0,0) is the top-left corner
    of the map, i.e. 180 deg W, 90 deg N."""
    x = (longitude + 180) / 360 * 1000
    y = (90 - latitude) / 180 * 500
    return round(x, 1), round(y, 1)


def offset_clustered_markers(records):
    """Facilities that render at (near-)identical pixels on the map --
    either because they share a site (SAAO's cluster, Mt John's two
    telescopes) or because two nearby-but-distinct sites round to the same
    pixel at this map scale (GTC and NOT are both on La Palma but not at
    the exact same coordinates) -- get spread within ~6px of each other in
    a small deterministic circle so they don't fully overlap. Grouped by
    *rendered* position, not raw lat/long, since that's what actually
    matters for legibility; precise on-mountain placement isn't meaningful
    for discovery either way."""
    by_pixel = {}
    for r in records:
        key = (round(r["marker_x"]), round(r["marker_y"]))
        by_pixel.setdefault(key, []).append(r)
    for group in by_pixel.values():
        if len(group) < 2:
            continue
        for i, r in enumerate(group):
            angle = 2 * math.pi * i / len(group)
            r["marker_x"] = round(r["marker_x"] + 6 * math.cos(angle), 1)
            r["marker_y"] = round(r["marker_y"] + 6 * math.sin(angle), 1)


def load_world_outline_path(svg_path):
    """Read the `d` attribute out of docs/_static/world-outline.svg so it
    can be inlined as a <path> inside the facility map's own <svg>, rather
    than referenced by URL (which would need a build-relative path that's
    fragile to compute correctly from inside a sphinx_jinja context). The
    static file remains the single source of truth -- see its header
    comment for provenance/licensing and how to regenerate it.

    `svg_path` is the location of that file; the caller decides where it is
    (see `ikp_data.loaders.build_contexts`)."""
    if not svg_path.exists():
        return ""
    match = re.search(r'<path\s+d="([^"]+)"', svg_path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""
