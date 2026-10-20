"""Contributed Software page: turn software YAML records into the page's data.

What the page needs
-------------------
``contributed-software.rst`` renders one card per software contribution, with
filters and free-text search. Records live in ``_data/software/<id>.yaml`` with
the same ``form_data`` / ``curated`` split as datasets (both pages are synced
by ``scripts/sync_contributions.py``). General Pool contributions are not in
this data set: every record here is Directable or Non-directable.

Why the derived fields exist
----------------------------
* ``status``: "delivered" or "pending" (or ``curated.status_override``).
* ``cid_slug``, ``last_updated``, ``filter_tokens``, ``search_text``: as for
  datasets.
* ``uat_keywords``: the team's own UAT answer if given, otherwise the sync
  script's guessed tags.
* ``software_links`` and ``documentation_links``: teams type several URLs into
  one free-text answer; these are split into (label, url) pairs so the card
  can show real links.
* ``approx_start``: the first fiscal year named in the free-text timeline, as a
  rough "started" hint (never a precise date).
* ``related``: "Also see" links, with titles looked up from the datasets and
  telescopes pages.
"""

import json
import re

import yaml

from ikp_data.derive import (
    collect_cross_page_targets,
    dataset_anchor,
    normalize_strings,
    record_last_updated,
    resolve_related_titles,
    slugify,
    telescope_anchor,
)


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


def load_software(data_dir, today):
    """Build the `contributed_software` context from `data_dir`/software."""
    records_dir = data_dir / "software"
    dataset_targets = collect_cross_page_targets(data_dir, "datasets", dataset_anchor)
    telescope_targets = collect_cross_page_targets(data_dir, "telescopes", telescope_anchor)

    records = []
    all_categories = set()
    all_uat = set()
    all_recipients = set()

    for path in sorted(records_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = normalize_strings(record)
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

        cid_slug = slugify(record.get("contribution_id", ""))
        record["cid_slug"] = cid_slug
        record["last_updated"] = record_last_updated(record, path)
        record["uat_keywords"] = uat_keywords
        record["software_links"] = _extract_links(form_data.get("software_url"))
        record["documentation_links"] = _extract_links(form_data.get("documentation"))
        record["approx_start"] = _approx_start_fy(form_data.get("timeline"))
        record["related"] = resolve_related_titles(
            curated.get("related_contribution_ids"),
            ("contributed-datasets.html", dataset_targets),
            ("contributed-telescope.html", telescope_targets),
        )

        tokens = [
            f"status-{slugify(status)}",
            f"cid-{cid_slug}",
            f"cat-{slugify(category)}",
        ]
        if primary_recipient:
            tokens.append(f"recipient-{slugify(primary_recipient)}")
        tokens += [f"uat-{slugify(v)}" for v in uat_keywords]
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
        "slugify": slugify,
        "search_index_json": json.dumps(search_index),
    }
