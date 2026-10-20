"""Contributed Datasets page: turn dataset YAML records into the page's data.

What the page needs
-------------------
``contributed-datasets.rst`` renders one card (and one table row) per dataset,
with filters, sorting and free-text search. Each record lives in
``_data/datasets/<contribution-id>.yaml`` as a ``form_data`` section (owned by
``scripts/sync_contributions.py``; safe to overwrite) and a ``curated`` section
(hand-edited only; the sync script never touches it).

Why the derived fields exist
----------------------------
The template and its filter script should not have to interpret raw answers, so
the loader adds, for every record:

* ``status``: the display status (``curated.status_override`` if set, else
  "available" or "not_yet_delivered" from whether data was submitted);
* ``cid_slug``: the contribution ID made safe for HTML ids and CSS classes;
* ``last_updated``: the date shown on the card (see ``ikp_data.derive``);
* ``related``: "Also see" links, with titles looked up from the software page;
* ``filter_tokens``: space-separated CSS-safe tokens the filter script matches;
* ``search_text``: lowercase text for the free-text search box.

The context also carries the sorted lists of filter choices, the ``slugify``
function (templates use it too) and the search index as JSON.
"""

import json

import yaml

from ikp_data.derive import (
    collect_cross_page_titles,
    normalize_strings,
    record_last_updated,
    resolve_related_titles,
    slugify,
)


def load_datasets(data_dir, today):
    """Build the `contributed_datasets` context from `data_dir`/datasets."""
    records_dir = data_dir / "datasets"
    # For the "Also see: software" reverse link -- mirrors the Contributed
    # Software page's own "Also see: dataset" link (curated.related_
    # contribution_ids there points at this page). Software title lookup
    # only, since a dataset card never links out to a Telescopes record.
    software_titles = collect_cross_page_titles(data_dir, "software")

    records = []
    all_data_types = set()
    all_wavelengths = set()
    all_uat = set()
    for path in sorted(records_dir.glob("*.yaml")):
        with path.open() as f:
            record = yaml.safe_load(f) or {}
        record = normalize_strings(record)
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

        cid_slug = slugify(record.get("contribution_id", ""))
        record["cid_slug"] = cid_slug
        record["last_updated"] = record_last_updated(record, path, today)
        record["related"] = resolve_related_titles(
            curated.get("related_contribution_ids"),
            ("contributed-software.html", software_titles),
        )

        # Space-separated CSS-safe tokens used by the page's filter/sort
        # script to match table rows and cards against the active filters.
        # cid- lets the free-text search script look a row/card back up in
        # the search index below without needing a raw data-* attribute on
        # sphinx-design's card markup (which only accepts CSS classes).
        tokens = [f"status-{slugify(status)}", f"cid-{cid_slug}"]
        tokens += [f"dt-{slugify(v)}" for v in data_types]
        tokens += [f"wl-{slugify(v)}" for v in wavelengths]
        tokens += [f"uat-{slugify(v)}" for v in uat_categories]
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
        "slugify": slugify,
        "search_index_json": json.dumps(search_index),
    }
