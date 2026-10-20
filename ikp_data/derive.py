"""Helpers shared by the card loaders (and by ``ikp_data.checks``).

Why this file exists
--------------------
The five loaders in ``ikp_data.loaders`` each turn raw YAML records into the
dictionaries the page templates render. They need the same small tools, so those
tools live here once instead of being copied into every loader (and into the
cross-record checks):

* text helpers: ``slugify`` and ``normalize_strings``;
* cross-page lookups: ``collect_cross_page_titles`` and ``resolve_related_titles``
  (how a card labels its "Also see" links to another page);
* the telescope fields that sibling records must agree on;
* map geometry: projecting latitude/longitude onto the world-outline SVG and
  nudging markers that would overlap;
* ``record_last_updated``: reads a card's explicit ``last_updated`` date.

Nothing in this module reads the clock, runs git, or locates files by itself:
callers pass in the dates and paths they want used.
"""

import math
import re
from pathlib import Path

import yaml

# Telescope fields that must be authored identically across sibling records that
# are the same facility at several sites. Used by the telescope loader (which
# warns at build time) and by ``ikp_data.checks`` (which reports a validation
# warning), so both always compare the same fields.
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


def collect_cross_page_titles(data_dir, subdir_name):
    """contribution_id -> title/facility lookup for a sibling _data folder,
    used to label a page's "Also see" cross-links to another page without
    needing that other page's full loader context. contribution_id may be
    a scalar or, on the Telescopes page, a list shared by sibling records.

    `data_dir` is the `_data` folder; `subdir_name` is the record type's
    folder inside it (for example "software").
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
            if c:
                out[c] = record.get("title") or record.get("facility") or c
    return out


def resolve_related_titles(related_ids, *page_lookups):
    """page_lookups is a sequence of (page_html_filename, {contribution_id: title})
    pairs, checked in order, so the returned dicts know which page to link to."""
    resolved = []
    for rid in related_ids or []:
        title = None
        page_url = None
        for page_html, lookup in page_lookups:
            if rid in lookup:
                title = lookup[rid]
                page_url = page_html
                break
        resolved.append({
            "contribution_id": rid,
            "title": title or rid,
            "slug": slugify(rid),
            "page_url": page_url,
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
            angle = 2 * 3.14159265 * i / len(group)
            r["marker_x"] = round(r["marker_x"] + 6 * _cos(angle), 1)
            r["marker_y"] = round(r["marker_y"] + 6 * _sin(angle), 1)


def _cos(x):
    return math.cos(x)


def _sin(x):
    return math.sin(x)


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
