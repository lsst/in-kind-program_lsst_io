import datetime
import json
import re
import subprocess
from pathlib import Path

import yaml

from documenteer.conf.guide import *  # noqa: F401 F403

html_theme_options = {
    "use_social_cards": False,
}


linkcheck_ignore = [
    r'https://astronomers\.salt\.ac\.za/.*',
    r'https://vidojevica\.aob\.rs/.*',
    # WISeREP (linked from the NOT facility card) returns 403 to
    # non-browser user agents, including sphinx's linkcheck bot -- the
    # link itself is valid, it's just blocking automated requests.
    r'https://www\.wiserep\.org/.*',
    # GTC and the INAF SIPGI proposal tool (linked from the GTC and LBT
    # facility cards) both serve incomplete SSL certificate chains --
    # real, reachable sites that browsers tolerate but Python's ssl
    # module rejects with CERTIFICATE_VERIFY_FAILED in CI.
    r'https://www\.gtc\.iac\.es/.*',
    r'https://pandora\.lambrate\.inaf\.it/.*',
    # SER-SAG-S1 (QhX AGN catalogue, linked from both the Datasets and
    # Software cards) serves an expired SSL certificate -- real,
    # reachable site that browsers tolerate but Python's ssl module
    # rejects with CERTIFICATE_VERIFY_FAILED in CI.
    r'https://ser-sag\.pmf\.kg\.ac\.rs.*',
]


# ============================================================================
# Contributed Datasets page data loading
#
# Each dataset record lives as a YAML file in
# docs/contribution-types/_data/datasets/<contribution-id>.yaml, split into
# a `form_data` section (owned by scripts/sync_contributions.py; safe to
# overwrite) and a `curated` section (hand-edited only; the sync script
# never touches it). This loader reads all records, resolves each one's
# display status, and exposes them to the contributed-datasets.rst page via
# sphinx_jinja.
# ============================================================================

def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _normalize_strings(obj):
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
        return [_normalize_strings(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _normalize_strings(v) for k, v in obj.items()}
    return obj


def _last_updated(path):
    """Best-effort "last updated" date for a single dataset record file.

    Prefers the file's most recent git commit date (accurate and portable
    across clones once the file has been committed). Falls back to the
    file's on-disk modification time for files that haven't been committed
    yet (e.g. during local review before a PR), so the page always shows
    something rather than a blank field.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", path.name],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=5,
        )
        date_str = result.stdout.strip()
        if date_str:
            return date_str
    except Exception:
        pass
    try:
        return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()
    except Exception:
        return None


def _load_contributed_datasets():
    data_dir = (
        Path(__file__).parent
        / "docs"
        / "contribution-types"
        / "_data"
        / "datasets"
    )
    records = []
    all_data_types = set()
    all_wavelengths = set()
    all_uat = set()
    for path in sorted(data_dir.glob("*.yaml")):
        with path.open() as f:
            record = yaml.safe_load(f) or {}
        record = _normalize_strings(record)
        form_data = record.setdefault("form_data", {}) or {}
        curated = record.setdefault("curated", {}) or {}
        status_override = curated.get("status_override")
        if status_override:
            status = status_override
        else:
            status = "available" if form_data.get("submitted") else "not_yet_delivered"
        record["status"] = status

        data_types = form_data.get("data_type") or []
        wavelengths = curated.get("wavelength_regime") or []
        uat_categories = form_data.get("uat_category") or []
        all_data_types.update(data_types)
        all_wavelengths.update(wavelengths)
        all_uat.update(uat_categories)

        cid_slug = _slugify(record.get("contribution_id", ""))
        record["cid_slug"] = cid_slug
        record["last_updated"] = _last_updated(path)

        # Space-separated CSS-safe tokens used by the page's filter/sort
        # script to match table rows and cards against the active filters.
        # cid- lets the free-text search script look a row/card back up in
        # the search index below without needing a raw data-* attribute on
        # sphinx-design's card markup (which only accepts CSS classes).
        tokens = [f"status-{_slugify(status)}", f"cid-{cid_slug}"]
        tokens += [f"dt-{_slugify(v)}" for v in data_types]
        tokens += [f"wl-{_slugify(v)}" for v in wavelengths]
        tokens += [f"uat-{_slugify(v)}" for v in uat_categories]
        record["filter_tokens"] = " ".join(tokens)

        # Free-text search covers the title, the curated summary/blurb, the
        # primary recipient, and the data type / wavelength / UAT "keyword"
        # tags -- lowercased for a simple case-insensitive substring search.
        search_parts = [
            record.get("title", ""),
            curated.get("summary", "") or "",
            curated.get("primary_recipient", "") or "",
            *data_types,
            *wavelengths,
            *uat_categories,
        ]
        record["search_text"] = " ".join(search_parts).lower()

        records.append(record)
    # Reverse chronological by last-updated -- the most recently touched
    # contributions surface first, since that's the signal visitors care
    # about. Missing dates sort to the bottom rather than the top.
    records.sort(key=lambda r: r.get("last_updated") or "", reverse=True)
    search_index = {r["cid_slug"]: r["search_text"] for r in records}
    return {
        "datasets": records,
        "all_data_types": sorted(all_data_types),
        "all_wavelengths": sorted(all_wavelengths),
        "all_uat": sorted(all_uat),
        "slugify": _slugify,
        "search_index_json": json.dumps(search_index),
    }


jinja_contexts = {
    "contributed_datasets": _load_contributed_datasets(),
}


# ============================================================================
# Contributed Telescope Access page data loading
#
# Each facility record lives as a YAML file in
# docs/contribution-types/_data/telescopes/<contribution-id>-<slug>.yaml.
# Unlike the datasets page, there is no external intake pipeline for
# telescope facility data -- the In-kind coordinator is the sole source of
# truth, so there is no form_data/curated split here, just a flat schema.
# This loader reads all records, derives hemisphere/map-marker position from
# coordinates, groups sibling records that share a contribution_id, and
# exposes everything to contributed-telescope.rst via sphinx_jinja.
# ============================================================================

_APERTURE_BAND_LABELS = {
    "small": "< 2m",
    "medium": "2-8m",
    "large": "> 8m",
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


def _to_marker_xy(latitude, longitude):
    """Equirectangular projection onto a 0-1000 x 0-500 canvas (matches the
    world-outline SVG's viewBox in _static/). (0,0) is the top-left corner
    of the map, i.e. 180 deg W, 90 deg N."""
    x = (longitude + 180) / 360 * 1000
    y = (90 - latitude) / 180 * 500
    return round(x, 1), round(y, 1)


def _offset_clustered_markers(records):
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
    import math
    return math.cos(x)


def _sin(x):
    import math
    return math.sin(x)


def _load_world_outline_path():
    """Read the `d` attribute out of docs/_static/world-outline.svg so it
    can be inlined as a <path> inside the facility map's own <svg>, rather
    than referenced by URL (which would need a build-relative path that's
    fragile to compute correctly from inside a sphinx_jinja context). The
    static file remains the single source of truth -- see its header
    comment for provenance/licensing and how to regenerate it."""
    path = (
        Path(__file__).parent / "docs" / "_static" / "world-outline.svg"
    )
    if not path.exists():
        return ""
    match = re.search(r'<path\s+d="([^"]+)"', path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


_STATUS_SORT_ORDER = {"available": 0, "future_semester": 1}
_SIBLING_CONSISTENCY_FIELDS = (
    "summary", "time_available", "duration", "status", "tac_process",
)


def _load_contributed_telescopes():
    data_dir = (
        Path(__file__).parent
        / "docs"
        / "contribution-types"
        / "_data"
        / "telescopes"
    )
    records = []
    all_instrumentation = set()
    all_wavelengths = set()
    resolution_bins_present = {}

    for path in sorted(data_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = _normalize_strings(record)

        contribution_id = record.get("contribution_id")
        contribution_ids = (
            contribution_id if isinstance(contribution_id, list) else [contribution_id]
        )
        record["contribution_ids"] = contribution_ids

        facility_slug = _slugify(record.get("facility", ""))
        record["facility_slug"] = facility_slug
        # Normalized (lowercase, hyphenated) so this exact string can be used
        # interchangeably as a CSS class token (`:class-item:` values are run
        # through docutils' class-name normalizer, which lowercases and
        # hyphenates automatically -- if `slug` weren't pre-normalized here,
        # the card's `slug-<slug>` class would silently end up spelled
        # differently than the raw `data-slug` attribute on the table row
        # and map marker, breaking search/highlight/scroll-to-card matching.
        record["slug"] = _slugify(path.stem)

        latitude = record.get("latitude")
        longitude = record.get("longitude")
        record["hemisphere"] = (
            "Northern" if (latitude or 0) >= 0 else "Southern"
        )
        if latitude is not None and longitude is not None:
            mx, my = _to_marker_xy(latitude, longitude)
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

        # Only two states are tracked ("available" / "future_semester") --
        # a facility whose availability isn't confirmed yet is future
        # semester by definition, so that's the safe default for a record
        # that omits `status` rather than a separate "tba" bucket.
        status = record.get("status", "future_semester")
        record["status"] = status
        tokens = [
            f"status-{_slugify(status)}",
            f"hemisphere-{_slugify(record['hemisphere'])}",
        ]
        if aperture_band:
            tokens.append(f"aperture-{aperture_band}")
        tokens += [f"instr-{_slugify(v)}" for v in instrumentation]
        tokens += [f"wl-{_slugify(v)}" for v in wavelengths]
        if record["resolution_bin"]:
            tokens.append(f"res-{record['resolution_bin']}")
        if record.get("multiplex") is True:
            tokens.append("multiplex-yes")
        for cid in contribution_ids:
            if cid:
                tokens.append(f"cid-{_slugify(cid)}")
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
        for field in _SIBLING_CONSISTENCY_FIELDS:
            values = {r.get(field) for r in group}
            if len(values) > 1 and logger is not None:
                logger.warning(
                    "[telescope-data] sibling records under contribution_id "
                    f"'{cid}' disagree on '{field}': "
                    f"{ {r['slug']: r.get(field) for r in group} }"
                )

    for r in records:
        r.setdefault("siblings", [])

    _offset_clustered_markers([r for r in records if "marker_x" in r])

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
        "slugify": _slugify,
        "search_index_json": json.dumps(search_index),
        "cid_to_slugs": cid_to_slugs,
        "world_outline_path": _load_world_outline_path(),
    }


def _load_contributed_opportunities():
    data_dir = (
        Path(__file__).parent
        / "docs"
        / "contribution-types"
        / "_data"
        / "opportunities"
    )
    today = datetime.date.today()
    records = []
    for path in sorted(data_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = _normalize_strings(record)
        record["slug"] = path.stem

        visible_until = record.get("visible_until")
        if isinstance(visible_until, str):
            visible_until = datetime.date.fromisoformat(visible_until)
        record["is_visible"] = visible_until is None or today <= visible_until

        milestones = record.get("milestones") or []
        upcoming = [
            m for m in milestones
            if isinstance(m.get("date"), (datetime.date, str))
        ]

        def _milestone_date(m):
            d = m.get("date")
            if isinstance(d, str):
                return datetime.date.fromisoformat(d)
            return d

        future_milestones = [m for m in upcoming if _milestone_date(m) >= today]
        record["next_milestone_date"] = (
            min((_milestone_date(m) for m in future_milestones), default=None)
        )
        records.append(record)

    visible_records = [r for r in records if r["is_visible"]]
    visible_records.sort(
        key=lambda r: (r["next_milestone_date"] is None, r["next_milestone_date"])
    )

    return {"opportunities": visible_records}


jinja_contexts["contributed_telescopes"] = _load_contributed_telescopes()
jinja_contexts["contributed_opportunities"] = _load_contributed_opportunities()
# The opportunities banner cross-links to facility cards by contribution_id,
# but anchors are per-card slugs (see cid_to_slugs above) -- shared here so
# that lookup works from the separate contributed_opportunities context too.
jinja_contexts["contributed_opportunities"]["cid_to_slugs"] = (
    jinja_contexts["contributed_telescopes"]["cid_to_slugs"]
)


# ============================================================================
# Contributed Software page data loading
#
# Each software-contribution record lives as a YAML file in
# docs/contribution-types/_data/software/<contribution-id>.yaml, split into
# a `form_data` section (owned by scripts/sync_contributions.py; safe to
# overwrite) and a `curated` section (hand-edited only; the sync script
# never touches it) -- same split as the Contributed Datasets page. Both
# pages are synced by the same script; see its module docstring.
# General Pool contributions are not part of this dataset at all (they have
# their own page); every record here is Directable or Non-directable.
# ============================================================================

def _software_status(record):
    curated = record.get("curated") or {}
    if curated.get("status_override"):
        return curated["status_override"]
    return "delivered" if (record.get("form_data") or {}).get("submitted") else "pending"


_URL_RE = re.compile(r"https?://[^\s,]+")
_FY_RE = re.compile(r"\bFY(\d{2})\b")


def _extract_links(text):
    """Split a free-text field like 'QhX source repository: <url>, package
    page: <url>' into individual (label, url) pairs. Team-submission form
    answers routinely list several URLs in one text blob rather than a
    single clean link; this pulls each one out with whatever label text
    preceded it so the card can render real clickable links instead of an
    unlinked wall of text."""
    if not text:
        return []
    links = []
    for segment in text.split(","):
        segment = segment.strip()
        match = _URL_RE.search(segment)
        if not match:
            continue
        url = match.group(0).rstrip(".,;)")
        label = segment[: match.start()].strip(" :")
        links.append({"label": label or url, "url": url})
    return links


def _approx_start_fy(timeline_text):
    """Best-effort 'start' signal pulled from the proposal spreadsheet's
    free-text Timeline column -- those are FTE-by-fiscal-year narratives
    (e.g. 'FY21: ... FY22: ...'), not a clean date, so this only ever
    surfaces the first FY mentioned as a rough indicator, never a precise
    start date."""
    if not timeline_text:
        return None
    match = _FY_RE.search(timeline_text)
    return f"FY{match.group(1)}" if match else None


def _resolve_related_titles(related_ids, *page_lookups):
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
            "slug": _slugify(rid),
            "page_url": page_url,
        })
    return resolved


def _load_contributed_software():
    data_dir = (
        Path(__file__).parent
        / "docs"
        / "contribution-types"
        / "_data"
        / "software"
    )
    dataset_titles = _collect_cross_page_titles("datasets")
    telescope_titles = _collect_cross_page_titles("telescopes")

    records = []
    all_categories = set()
    all_uat = set()
    all_recipients = set()

    for path in sorted(data_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = _normalize_strings(record)
        form_data = record.setdefault("form_data", {}) or {}
        curated = record.setdefault("curated", {}) or {}

        status = _software_status(record)
        record["status"] = status

        category = form_data.get("category") or "Unknown"
        # Real UAT answers from a team's own form submission take
        # precedence over the sync script's keyword-guessed curated tags.
        uat_keywords = form_data.get("uat_category") or curated.get("uat_keywords") or []
        primary_recipient = form_data.get("primary_recipient_group") or ""

        all_categories.add(category)
        all_uat.update(uat_keywords)
        if primary_recipient:
            all_recipients.add(primary_recipient)

        cid_slug = _slugify(record.get("contribution_id", ""))
        record["cid_slug"] = cid_slug
        record["last_updated"] = _last_updated(path)
        record["uat_keywords"] = uat_keywords
        record["software_links"] = _extract_links(form_data.get("software_url"))
        record["documentation_links"] = _extract_links(form_data.get("documentation"))
        record["approx_start"] = _approx_start_fy(form_data.get("timeline"))
        record["related"] = _resolve_related_titles(
            curated.get("related_contribution_ids"),
            ("contributed-datasets.html", dataset_titles),
            ("contributed-telescope.html", telescope_titles),
        )

        tokens = [
            f"status-{_slugify(status)}",
            f"cid-{cid_slug}",
            f"cat-{_slugify(category)}",
        ]
        if primary_recipient:
            tokens.append(f"recipient-{_slugify(primary_recipient)}")
        tokens += [f"uat-{_slugify(v)}" for v in uat_keywords]
        record["filter_tokens"] = " ".join(tokens)

        search_parts = [
            record.get("title", ""),
            form_data.get("activity_description", "") or "",
            primary_recipient,
            *(form_data.get("additional_recipient_groups") or []),
            *uat_keywords,
        ]
        record["search_text"] = " ".join(search_parts).lower()

        records.append(record)

    records.sort(key=lambda r: r.get("last_updated") or "", reverse=True)
    search_index = {r["cid_slug"]: r["search_text"] for r in records}
    return {
        "software": records,
        "all_categories": sorted(all_categories),
        "all_uat": sorted(all_uat),
        "all_recipients": sorted(all_recipients),
        "slugify": _slugify,
        "search_index_json": json.dumps(search_index),
    }


def _collect_cross_page_titles(subdir_name):
    """contribution_id -> title/facility lookup for a sibling _data folder,
    used to label the Contributed Software page's "Also see" cross-links
    without needing that page's full loader context. contribution_id may be
    a scalar or, on the Telescopes page, a list shared by sibling records."""
    data_dir = (
        Path(__file__).parent
        / "docs"
        / "contribution-types"
        / "_data"
        / subdir_name
    )
    out = {}
    if not data_dir.exists():
        return out
    for path in sorted(data_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        cid = record.get("contribution_id")
        cids = cid if isinstance(cid, list) else [cid]
        for c in cids:
            if c:
                out[c] = record.get("title") or record.get("facility") or c
    return out


jinja_contexts["contributed_software"] = _load_contributed_software()


# ============================================================================
# APPEND THIS BLOCK TO conf.py (at the repo root), after the existing
# `jinja_contexts["contributed_software"] = _load_contributed_software()` line.
#
# It reuses helpers already defined earlier in conf.py:
#   _slugify, _normalize_strings, _to_marker_xy,
#   _offset_clustered_markers, _load_world_outline_path
# ============================================================================

# ============================================================================
# Contributed Computing Resources (IDAC / SPC) page data loading
#
# Each record lives as a YAML file in
# docs/contribution-types/_data/idacs/<slug>.yaml. Like the telescopes page,
# the In-kind coordinator is the source of truth (there is no external form
# intake), so there is no form_data/curated split -- just a flat, hand-curated
# schema. This loader reuses the equirectangular _to_marker_xy() projection and
# the world-outline SVG from the telescopes loader above, sizes each marker by
# its storage commitment, and exposes everything to contributed-resources.rst
# via sphinx_jinja.
# ============================================================================

_IDAC_PRODUCT_LABELS = {
    "object_table_subset": "Object Table (subset)",
    "object_table": "Object Table",
    "source_table": "Source Table",
    "forced_source_table": "ForcedSource Table",
    "dia_object_table": "DIAObject Table",
    "dia_source_table": "DIASource Table",
    "solar_system_tables": "Solar System Tables",
    "co_added_images": "Co-added Images",
    "visit_images": "Visit Images",
    "difference_images": "Difference Images",
    "template_images": "Template Images",
    "other_data_products": "Other Data Products",
}


def _idac_marker_radius(storage, max_storage):
    """Scale a marker radius by the square root of the storage commitment so
    the map echoes the relative scale of each IDAC (bounded so the smallest
    contributions stay clickable and the largest don't swamp the map)."""
    if not storage or not max_storage:
        return 4.0
    return round(4.0 + 8.0 * (storage / max_storage) ** 0.5, 1)


def _load_contributed_idacs():
    data_dir = (
        Path(__file__).parent
        / "docs"
        / "contribution-types"
        / "_data"
        / "idacs"
    )
    records = []
    all_types = set()
    all_products = set()

    raw = []
    for path in sorted(data_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = _normalize_strings(record)
        record["slug"] = _slugify(record.get("slug") or path.stem)
        raw.append((path, record))

    max_storage = max(
        ((r.get("capacity") or {}).get("storage_pb_years") or 0) for _, r in raw
    ) if raw else 0

    for path, record in raw:
        loc = record.get("location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is not None and lng is not None:
            record["marker_x"], record["marker_y"] = _to_marker_xy(lat, lng)
        else:
            record["marker_x"] = record["marker_y"] = None

        cap = record.get("capacity") or {}
        record["marker_r"] = _idac_marker_radius(cap.get("storage_pb_years"), max_storage)

        idac_type = record.get("idac_type") or "IDAC"
        record["idac_type"] = idac_type
        all_types.add(idac_type)

        products = record.get("data_products") or {}
        hosted = [
            _IDAC_PRODUCT_LABELS[k]
            for k in _IDAC_PRODUCT_LABELS
            if products.get(k)
        ]
        record["hosted_products"] = hosted
        record["product_count"] = len(hosted)
        record["product_total"] = len(_IDAC_PRODUCT_LABELS)
        all_products.update(hosted)

        # Space-separated CSS-safe tokens the page's filter script matches
        # table rows, cards, and map markers against.
        tokens = [f"type-{_slugify(idac_type)}", f"cid-{record['slug']}"]
        tokens += [f"product-{_slugify(p)}" for p in hosted]
        if cap.get("gpu_mhrs"):
            tokens.append("has-gpu")
        record["filter_tokens"] = " ".join(tokens)

        search_parts = [
            record.get("country", ""),
            loc.get("city", "") or "",
            loc.get("institution", "") or "",
            idac_type,
            record.get("software_services", "") or "",
            record.get("use_cases", "") or "",
            record.get("complementary_datasets", "") or "",
            record.get("science_collaboration_agreements", "") or "",
            *hosted,
        ]
        record["search_text"] = " ".join(p for p in search_parts if p).lower()
        records.append(record)

    _offset_clustered_markers([r for r in records if r.get("marker_x") is not None])
    records.sort(key=lambda r: r.get("country", ""))
    search_index = {r["slug"]: r["search_text"] for r in records}

    return {
        "idacs": records,
        "all_types": sorted(all_types),
        "all_products": sorted(all_products),
        "product_labels": _IDAC_PRODUCT_LABELS,
        "slugify": _slugify,
        "search_index_json": json.dumps(search_index),
        "world_outline_path": _load_world_outline_path(),
    }


jinja_contexts["contributed_idacs"] = _load_contributed_idacs()
