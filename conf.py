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
]


# ============================================================================
# Contributed Datasets page data loading
#
# Each dataset record lives as a YAML file in
# docs/contribution-types/_data/datasets/<contribution-id>.yaml, split into
# a `form_data` section (owned by the CSV pull script; safe to overwrite)
# and a `curated` section (hand-edited only; the pull script never touches
# it). This loader reads all records, resolves each one's display status,
# and exposes them to the contributed-datasets.rst page via sphinx_jinja.
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

