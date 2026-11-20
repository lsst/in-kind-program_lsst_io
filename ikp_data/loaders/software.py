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
* ``status``: "available" or "pending" (or ``curated.status_override``).
* ``display_version``: ``curated.version`` if set, otherwise
  ``form_data.version``. The card shows it on Available cards only.
* ``display_country``: the country as the card header spells it (for example
  "UK" shows as "United Kingdom").
* ``description_html``: the activity description, safe to place inside the
  card's ``.. raw:: html`` block (see ``_description_html``).
* ``anchor`` (``sw-cid-<contribution ID slug>``), ``last_updated``,
  ``filters`` and ``search_text``: as for datasets.
* ``uat_keywords``: the team's own UAT answer if given, otherwise the sync
  script's guessed tags.
* ``software_links`` and ``documentation_links``: teams type several URLs into
  one free-text answer; these are split into (label, url) pairs so the card
  can show real links.
* ``approx_start``: the first fiscal year named in the free-text timeline, as a
  rough "started" hint (never a precise date).
* ``related``: "Also see" links to dataset cards (another page) or to other
  software cards (this page), with titles looked up from the records.
  (``ikp_data.checks`` ensures related IDs name datasets or software, never
  telescopes.)

The records are in page order, Available first (see ``ikp_data.derive.sort_cards``);
the cards and the table rows share it.
"""

import html
import re

import yaml

from ikp_data.derive import (
    collect_cross_page_targets,
    dataset_anchor,
    display_country,
    normalize_strings,
    option_pairs,
    record_last_updated,
    resolve_related_titles,
    search_index_to_json,
    slugify,
    software_anchor,
    sort_cards,
)


def _software_status(record):
    curated = record.get("curated") or {}
    if curated.get("status_override"):
        return curated["status_override"]
    return "available" if (record.get("form_data") or {}).get("submitted") else "pending"


def _description_html(text):
    """The activity description as text that is safe inside a raw HTML block.

    The card writes the description straight into HTML, so any ``<`` or ``&`` in
    a team's answer would be read as markup. Some answers already contain an
    entity such as ``&amp;``. Decoding first, then escaping, shows each one as
    the character the author meant, and escaping every time means a ``<script>``
    in an answer can only ever appear as text. An empty description shows "TBD".
    """
    if not text:
        return "TBD"
    return html.escape(html.unescape(text))


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
    # `today` is accepted so every loader has the same signature (and so date-based
    # features, such as expiring highlights, can use it later).
    records_dir = data_dir / "software"
    # For the "Also see" links: a related ID is looked up on the Datasets page
    # first (the usual case: the matching dataset card), then on this page
    # (another software item).
    dataset_targets = collect_cross_page_targets(data_dir, "datasets", dataset_anchor)
    software_targets = collect_cross_page_targets(data_dir, "software", software_anchor)

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

        record["anchor"] = software_anchor(path, record.get("contribution_id", ""))
        record["last_updated"] = record_last_updated(record, path)
        record["display_country"] = display_country(record.get("country"))
        # A curated version wins over the form's free-text answer, which can be
        # long or awkward to show on a card.
        record["display_version"] = curated.get("version") or form_data.get("version")
        record["description_html"] = _description_html(form_data.get("activity_description"))
        record["uat_keywords"] = uat_keywords
        record["software_links"] = _extract_links(form_data.get("software_url"))
        record["documentation_links"] = _extract_links(form_data.get("documentation"))
        record["approx_start"] = _approx_start_fy(form_data.get("timeline"))
        record["related"] = resolve_related_titles(
            curated.get("related_contribution_ids"),
            ("contributed-datasets.html", dataset_targets, "dataset"),
            ("contributed-software.html", software_targets, "software"),
            current_page="contributed-software.html",
            own_id=record.get("contribution_id"),
        )

        # The tokens this item has for each filter, keyed by the drop-down's
        # `data-filter-key` (see the datasets loader).
        record["filters"] = {
            "status": [f"status-{slugify(status)}"],
            "cat": [f"cat-{slugify(category)}"],
            "recipient": [f"recipient-{slugify(primary_recipient)}"] if primary_recipient else [],
            "uat": [f"uat-{slugify(v)}" for v in uat_keywords],
        }

        search_parts = [
            record.get("title", ""),
            form_data.get("activity_description", "") or "",
            primary_recipient,
            *(form_data.get("additional_recipient_groups") or []),
            *uat_keywords,
        ]
        record["search_text"] = " ".join(search_parts).lower()

        records.append(record)

    # Available first, then the most recently updated (see `sort_cards`).
    records = sort_cards(records)
    search_index = {r["anchor"]: r["search_text"] for r in records}
    return {
        "software": records,
        "all_categories": option_pairs(all_categories),
        "all_uat": option_pairs(all_uat),
        "all_recipients": option_pairs(all_recipients),
        "search_index_json": search_index_to_json(search_index),
    }
