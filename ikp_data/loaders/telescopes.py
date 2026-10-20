"""Contributed Telescopes page: turn facility YAML records into the page's data.

What the page needs
-------------------
``contributed-telescope.rst`` renders a table, a world map and one card per
facility, with filters, sorting and free-text search. Each facility is a flat
YAML file, ``_data/telescopes/<contribution-id>-<slug>.yaml``. There is no
external intake pipeline for telescope data (the In-kind coordinator is the
source of truth), so unlike datasets and software there is no
``form_data``/``curated`` split.

Why the derived fields exist
----------------------------
* ``contribution_ids``: ``contribution_id`` is a single ID or a list (several
  facilities can be funded by one contribution); templates get a list always.
* ``facility_slug`` and ``slug``: stable, CSS-safe anchors. The slug comes from
  the file name because ``contribution_id`` is not unique per card.
* ``hemisphere``, ``marker_x`` / ``marker_y``: where the facility sits on the
  map, projected from latitude/longitude (see ``ikp_data.derive``).
* ``aperture_band`` and ``resolution_bin``: coarse buckets for the filters.
* ``status``: defaults to "future_semester" when a record omits it.
* ``filter_tokens`` and ``search_text``: what the filter and search scripts match.
* ``siblings``: links between records that share a ``contribution_id`` (for
  example KMTNet's three sites), plus a build-time warning if fields that
  should be identical across same-facility siblings have drifted.
* ``cid_to_slugs``: contribution ID -> the card slugs for it, used by the
  opportunities banner to link to facility cards.
"""

import json
import re

import yaml

from ikp_data.derive import (
    SIBLING_CONSISTENCY_FIELDS,
    load_world_outline_path,
    normalize_strings,
    offset_clustered_markers,
    require_field,
    slugify,
    to_marker_xy,
)

_APERTURE_BAND_LABELS = {
    "small": "&lt; 2m",
    "medium": "2-8m",
    "large": "&gt; 8m",
}


def _aperture_band(aperture_str):
    """Bucket a free-text aperture string (e.g. "2 x 8.4m", "1.9m-1.0m")
    into a coarse band using the largest diameter mentioned, since that's
    the figure that matters most for feasibility at a glance."""
    if not aperture_str:
        return None
    numbers = [float(n) for n in re.findall(r"\d+\.?\d*", aperture_str)]
    if not numbers:
        return None
    largest = max(numbers)
    if largest < 2:
        return "small"
    if largest <= 8:
        return "medium"
    return "large"


def _resolution_bin(r_min, r_max):
    """Bucket a spectral-resolution range into a filter bin whose label
    states the real R boundary explicitly (never "low"/"medium"/"high" on
    their own), since different subdisciplines draw that line differently.
    Uses the midpoint of the range when both bounds are given."""
    if r_min is None and r_max is None:
        return None
    values = [v for v in (r_min, r_max) if v is not None]
    midpoint = sum(values) / len(values)
    if midpoint < 1000:
        return "r-lt-1000", "R < 1,000"
    if midpoint < 5000:
        return "r-1000-5000", "1,000 <= R < 5,000"
    return "r-gte-5000", "R >= 5,000"


_STATUS_SORT_ORDER = {"available": 0, "future_semester": 1, "past_opportunity": 2}


def load_telescopes(data_dir, world_outline_svg):
    """Build the `contributed_telescopes` context from `data_dir`/telescopes.

    `world_outline_svg` is the path of the world-outline SVG used by the map.
    """
    records_dir = data_dir / "telescopes"
    records = []
    all_instrumentation = set()
    all_wavelengths = set()
    resolution_bins_present = {}

    for path in sorted(records_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = normalize_strings(record)

        contribution_id = record.get("contribution_id")
        contribution_ids = (
            contribution_id if isinstance(contribution_id, list) else [contribution_id]
        )
        record["contribution_ids"] = contribution_ids

        facility_slug = slugify(record.get("facility", ""))
        record["facility_slug"] = facility_slug
        # Normalized (lowercase, hyphenated) so this exact string can be used
        # interchangeably as a CSS class token (`:class-item:` values are run
        # through docutils' class-name normalizer, which lowercases and
        # hyphenates automatically -- if `slug` weren't pre-normalized here,
        # the card's `slug-<slug>` class would silently end up spelled
        # differently than the raw `data-slug` attribute on the table row
        # and map marker, breaking search/highlight/scroll-to-card matching.
        record["slug"] = slugify(path.stem)

        # The schema requires latitude, so a missing value is an error naming
        # the file rather than a silent "Northern" default. Longitude is
        # optional: without it the facility simply gets no map marker.
        latitude = require_field(record, "latitude", path)
        longitude = record.get("longitude")
        record["hemisphere"] = "Northern" if latitude >= 0 else "Southern"
        if longitude is not None:
            mx, my = to_marker_xy(latitude, longitude)
            record["marker_x"], record["marker_y"] = mx, my

        aperture_band = _aperture_band(record.get("aperture"))
        record["aperture_band"] = aperture_band

        instrumentation = record.get("instrumentation") or []
        wavelengths = record.get("wavelength_regime") or []
        all_instrumentation.update(instrumentation)
        all_wavelengths.update(wavelengths)

        res_bin = _resolution_bin(
            record.get("spectral_resolution_min"),
            record.get("spectral_resolution_max"),
        )
        if res_bin:
            record["resolution_bin"], record["resolution_bin_label"] = res_bin
            resolution_bins_present[res_bin[0]] = res_bin[1]
        else:
            record["resolution_bin"] = None
            record["resolution_bin_label"] = None

        # Three states are tracked: "available", "future_semester", and
        # "past_opportunity" (a facility/opportunity that has closed). A
        # facility whose availability isn't confirmed yet is future
        # semester by definition, so that's the safe default for a record
        # that omits `status` rather than a separate "tba" bucket.
        status = record.get("status", "future_semester")
        record["status"] = status
        tokens = [
            f"status-{slugify(status)}",
            f"hemisphere-{slugify(record['hemisphere'])}",
        ]
        if aperture_band:
            tokens.append(f"aperture-{aperture_band}")
        tokens += [f"instr-{slugify(v)}" for v in instrumentation]
        tokens += [f"wl-{slugify(v)}" for v in wavelengths]
        if record["resolution_bin"]:
            tokens.append(f"res-{record['resolution_bin']}")
        if record.get("multiplex") is True:
            tokens.append("multiplex-yes")
        for cid in contribution_ids:
            if cid:
                tokens.append(f"cid-{slugify(cid)}")
        record["filter_tokens"] = " ".join(tokens)

        search_parts = [
            record.get("facility", ""),
            record.get("site", "") or "",
            record.get("country", "") or "",
            record.get("summary", "") or "",
            *instrumentation,
            *(record.get("instrument_names") or []),
            *contribution_ids,
        ]
        record["search_text"] = " ".join(p for p in search_parts if p).lower()

        records.append(record)

    # Group sibling records sharing a contribution_id (KMTNet's 3 sites,
    # Mt John's 2 telescopes, VST/LBT) for the "also available under this
    # contribution" cross-link, and warn at build time if fields that
    # should be authored identically across siblings have drifted --
    # catches copy/paste mistakes before they render as inconsistent cards.
    by_cid = {}
    for r in records:
        for cid in r["contribution_ids"]:
            if cid:
                by_cid.setdefault(cid, []).append(r)

    try:
        from sphinx.util import logging as sphinx_logging
        logger = sphinx_logging.getLogger(__name__)
    except Exception:
        logger = None

    for cid, group in by_cid.items():
        if len(group) < 2:
            continue
        for r in group:
            siblings = [
                {
                    "facility": s["facility"],
                    "site": s.get("site"),
                    "slug": s["slug"],
                    # When siblings share the same facility name (KMTNet's
                    # three near-identical sites), the site is the only
                    # thing that actually distinguishes them in a
                    # cross-link list -- append it whenever a name
                    # collision would otherwise make two links read
                    # identically.
                    "label": (
                        f"{s['facility']} ({s['site']})"
                        if s.get("site") and any(
                            o["facility"] == s["facility"] and o["slug"] != s["slug"]
                            for o in group
                        )
                        else s["facility"]
                    ),
                }
                for s in group
                if s["slug"] != r["slug"]
            ]
            r.setdefault("siblings", [])
            for s in siblings:
                if s not in r["siblings"]:
                    r["siblings"].append(s)
        # Only enforce agreement across siblings that are the *same*
        # facility replicated at multiple sites (KMTNet's three near-
        # identical telescopes, per Section 4 of the requirements doc).
        # Siblings that are materially different facilities sharing a
        # contribution_id purely for funding reasons (VST/LBT, McLellan/
        # Nishimura) are expected to have their own distinct summary,
        # time_available, etc. -- checking those would just be noise.
        facility_names = {r.get("facility") for r in group}
        if len(facility_names) > 1:
            continue
        for field in SIBLING_CONSISTENCY_FIELDS:
            values = {r.get(field) for r in group}
            if len(values) > 1 and logger is not None:
                logger.warning(
                    "[telescope-data] sibling records under contribution_id "
                    f"'{cid}' disagree on '{field}': "
                    f"{ {r['slug']: r.get(field) for r in group} }"
                )

    for r in records:
        r.setdefault("siblings", [])

    offset_clustered_markers([r for r in records if "marker_x" in r])

    records.sort(
        key=lambda r: (
            _STATUS_SORT_ORDER.get(r.get("status"), 99),
            r.get("facility", ""),
        )
    )
    search_index = {r["slug"]: r["search_text"] for r in records}

    # Each record's own slug (from its filename) is its unique anchor --
    # contribution_id is NOT unique per card (KMTNet's three sibling
    # records all share KOR-KAS-S2), so anything that needs to link to
    # "the card(s) for this contribution" -- like the opportunities
    # banner -- looks it up here rather than anchoring directly on the
    # contribution_id.
    cid_to_slugs = {}
    for r in records:
        for cid in r["contribution_ids"]:
            if cid:
                cid_to_slugs.setdefault(cid, []).append(r["slug"])

    return {
        "telescopes": records,
        "all_instrumentation": sorted(all_instrumentation),
        "all_wavelengths": sorted(all_wavelengths),
        "all_resolution_bins": sorted(resolution_bins_present.items()),
        "all_aperture_bands": [
            (k, v) for k, v in _APERTURE_BAND_LABELS.items()
        ],
        "slugify": slugify,
        "search_index_json": json.dumps(search_index),
        "cid_to_slugs": cid_to_slugs,
        "world_outline_path": load_world_outline_path(world_outline_svg),
    }
