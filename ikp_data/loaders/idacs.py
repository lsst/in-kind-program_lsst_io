"""Contributed Computing Resources page: turn IDAC YAML records into data.

What the page needs
-------------------
``contributed-resources.rst`` shows a world map, table and cards of Rubin Data
Access Centers (IDACs) and similar computing contributions. Each is a flat
YAML file, ``_data/idacs/<slug>.yaml``; like telescopes, the In-kind
coordinator is the source of truth, so there is no ``form_data``/``curated``
split.

Why the derived fields exist
----------------------------
* ``slug``: a CSS-safe anchor (the record's ``slug`` or its file name).
* ``marker_x`` / ``marker_y``: map position, using the same projection as the
  telescopes map (see ``ikp_data.derive``); ``marker_r`` sizes each marker by
  its storage commitment.
* ``hosted_products``, ``product_count``, ``product_total``: which of the
  known data products the site hosts, in a fixed display order.
* ``filter_tokens`` and ``search_text``: what the filter and search scripts match.
"""

import json

import yaml

from ikp_data.derive import (
    load_world_outline_path,
    normalize_strings,
    offset_clustered_markers,
    slugify,
    to_marker_xy,
)


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


def load_idacs(data_dir, world_outline_svg):
    """Build the `contributed_idacs` context from `data_dir`/idacs.

    `world_outline_svg` is the path of the world-outline SVG used by the map.
    """
    records_dir = data_dir / "idacs"
    records = []
    all_types = set()
    all_products = set()

    raw = []
    for path in sorted(records_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = normalize_strings(record)
        record["slug"] = slugify(record.get("slug") or path.stem)
        raw.append((path, record))

    max_storage = max(
        ((r.get("capacity") or {}).get("storage_pb_years") or 0) for _, r in raw
    ) if raw else 0

    for path, record in raw:
        loc = record.get("location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is not None and lng is not None:
            record["marker_x"], record["marker_y"] = to_marker_xy(lat, lng)
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
        tokens = [f"type-{slugify(idac_type)}", f"cid-{record['slug']}"]
        tokens += [f"product-{slugify(p)}" for p in hosted]
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

    offset_clustered_markers([r for r in records if r.get("marker_x") is not None])
    records.sort(key=lambda r: r.get("country", ""))
    search_index = {r["slug"]: r["search_text"] for r in records}

    return {
        "idacs": records,
        "all_types": sorted(all_types),
        "all_products": sorted(all_products),
        "product_labels": _IDAC_PRODUCT_LABELS,
        "slugify": slugify,
        "search_index_json": json.dumps(search_index),
        "world_outline_path": load_world_outline_path(world_outline_svg),
    }
