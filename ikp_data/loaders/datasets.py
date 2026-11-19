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
* ``anchor``: the id of the dataset's card on the page (``ds-cid-<contribution ID slug>``).
  Table rows carry it as ``data-card`` so the filter script can find the card;
* ``last_updated``: the date shown on the card (see ``ikp_data.derive``);
* ``related``: "Also see" links, with titles looked up from the software page;
* ``filters``: for each filter key (the ``data-filter-key`` of a drop-down, or the
  "available only" button), the tokens this dataset has. The template writes each
  entry onto the table row as a ``data-filter-<key>`` attribute;
* ``search_text``: lowercase text for the free-text search box.

The context also carries the filter drop-down options as sorted ``(label, slug)``
pairs and the search index as JSON.
"""

import yaml

from ikp_data.derive import (
    collect_cross_page_targets,
    dataset_anchor,
    normalize_strings,
    option_pairs,
    record_last_updated,
    resolve_related_titles,
    search_index_to_json,
    slugify,
    software_anchor,
)


def load_datasets(data_dir, today):
    """Build the `contributed_datasets` context from `data_dir`/datasets."""
    # `today` is accepted so every loader has the same signature (and so date-based
    # features, such as expiring highlights, can use it later).
    records_dir = data_dir / "datasets"
    # For the "Also see: software" reverse link -- mirrors the Contributed
    # Software page's own "Also see: dataset" link (curated.related_
    # contribution_ids there points at this page). Software title lookup
    # only, since a dataset card never links out to a Telescopes record.
    software_targets = collect_cross_page_targets(data_dir, "software", software_anchor)

    records = []
    all_data_types = set()
    all_wavelengths = set()
    all_uat = set()
    for path in sorted(records_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
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

        record["anchor"] = dataset_anchor(path, record.get("contribution_id", ""))
        record["last_updated"] = record_last_updated(record, path)
        record["related"] = resolve_related_titles(
            curated.get("related_contribution_ids"),
            ("contributed-software.html", software_targets),
        )

        # The tokens this dataset has for each filter, keyed by the filter's
        # `data-filter-key`. Each token is the `value` of one option of that
        # filter (the "available only" button asks for `status-available`).
        record["filters"] = {
            "status": [f"status-{slugify(status)}"],
            "dt": [f"dt-{slugify(v)}" for v in data_types],
            "wl": [f"wl-{slugify(v)}" for v in wavelengths],
            "uat": [f"uat-{slugify(v)}" for v in uat_categories],
        }

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
    search_index = {r["anchor"]: r["search_text"] for r in records}
    return {
        "datasets": records,
        "all_data_types": option_pairs(all_data_types),
        "all_wavelengths": option_pairs(all_wavelengths),
        "all_uat": option_pairs(all_uat),
        "search_index_json": search_index_to_json(search_index),
    }
