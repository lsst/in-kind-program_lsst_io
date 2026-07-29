#!/usr/bin/env python3
"""Sync docs/contribution-types/_data/{software,datasets}/*.yaml from source CSVs.

One script, two card types.

  --form-responses  REQUIRED in practice. The "In-kind Contribution
                     Resources" Google Form export. This is the ongoing,
                     day-to-day input -- every time a team submits (or
                     edits) their closing-form response, re-export this
                     sheet and re-run the script. Each row's "Contribution
                     deliverable type" answer routes it to one of three
                     places:
                       - "Software"  -> docs/.../_data/software/<id>.yaml
                       - "Datasets"  -> docs/.../_data/datasets/<id>.yaml
                       - a Software row that also answers "Yes" to data
                         products gets an `associated_dataset` block, and
                         that same data is also written to a companion
                         Datasets card for that ID -- created fresh
                         (flagged needs_review) if none exists yet, e.g.
                         SER-SAG-S1, or, going through the normal
                         review-diff gate like any other update, merged
                         into one that already exists (e.g. one of the
                         original pre-delivery placeholder cards).
  --contributions   OPTIONAL, rare. The proposal-spreadsheet export (one row
                     per contribution; columns: Country, Institute, ID,
                     Contribution Title, Scraped Recipient Group, SOW,
                     Timeline, Category, Recipient Group(s), Primary
                     Recipient Group, Activity Description). This was a
                     one-off used to bulk-populate the initial set of
                     software cards (with a "pending" placeholder for every
                     proposed contribution, submitted or not) and isn't
                     expected to be re-pulled going forward. If you do
                     supply it, it's only used to fill in identity fields
                     (title/country/institute/category/recipient/timeline)
                     for a contribution ID when a form response doesn't
                     already have a card on disk for that ID.

Without --contributions, a contribution (software or dataset) only gets a
card once its closing form response actually arrives -- there's no more
automatic "pending" placeholder for a newly proposed contribution. If you
want one to show up as pending before it's submitted, hand-create a bare
YAML file for it first (title/country/institute only, `submitted: false`),
the same way the original 16 dataset cards were backfilled -- the sync
script will then update that file in place once a response comes in.

Both card types split their YAML into a `form_data` section (owned by this
script; regenerated from the CSVs every run) and a `curated` section
(hand-edited only; this script writes it once on first creation and never
touches it again). Title/country/institute on an *existing* record are
treated as protected once set (Datasets always; Software too, now that
identity mostly comes from the form rather than a re-pulled spreadsheet)
-- only assigned when a card is first created, never overwritten after.

Review gate: this script never silently overwrites an *existing* card's
form_data. Whenever a CSV re-read would change something on a record that's
already on disk -- a genuine new submission, a resubmission, or a team
editing their existing form response in place without resubmitting -- it
prints a per-field before/after diff and asks whether to apply it. Pass
--yes to skip the prompts and apply every change (e.g. for a first bulk
sync). Brand-new cards (no existing file) are always created outright and
flagged needs_review rather than gated, since there's nothing to overwrite.

Safe to re-run otherwise: skip a prompt (or answer "n") and that record's
file is left completely untouched.
"""
import argparse
import csv
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOFTWARE_DIR = REPO_ROOT / "docs" / "contribution-types" / "_data" / "software"
DATASETS_DIR = REPO_ROOT / "docs" / "contribution-types" / "_data" / "datasets"
TELESCOPES_DIR = REPO_ROOT / "docs" / "contribution-types" / "_data" / "telescopes"

CATEGORY_LABELS = {
    "4.2": "Directable SW dev",
    "4.3": "Non-directable SW dev",
}

# --- UAT keyword guesser (software only) --------------------------------
# Used only until a record's real team-submission form response arrives
# with actual "UAT Category"/"Specific UAT Concepts" answers -- this is a
# coarse, reviewable starting guess, not a substitute for real curation.
RECIPIENT_KEYWORDS = {
    "dark energy": ["Cosmology"],
    "galaxies": ["Galaxies"],
    "transients and variable stars": ["Time domain astronomy", "Transient detection"],
    "agn": ["Active galactic nuclei"],
    "solar system": ["Solar system astronomy"],
    "strong lensing": ["Strong gravitational lensing", "Gravitational lensing"],
    "stars milky way": ["Variable stars"],
    "crowded field": ["Stellar photometry"],
}
TEXT_KEYWORDS = {
    "photo-z": ["Photometric redshift"],
    "photometric redshift": ["Photometric redshift"],
    "lensing": ["Gravitational lensing"],
    "machine learning": ["Machine learning"],
    "deep learning": ["Deep learning", "Machine learning"],
    "spectroscop": ["Spectroscopy"],
    "transient": ["Transient detection", "Time domain astronomy"],
    "variable star": ["Variable stars"],
    "supernova": ["Supernovae"],
    "quasar": ["Active galactic nuclei"],
    " agn": ["Active galactic nuclei"],
    "cluster": ["Galaxy clusters"],
    "radio": ["Radio astronomy"],
    "pipeline": ["Astronomy software"],
    "software": ["Astronomy software"],
    "catalog": ["Astroinformatics"],
    "database": ["Astroinformatics"],
    "citizen science": ["Citizen science"],
    "high performance comput": ["High performance computing"],
    "visualiz": ["Data visualization"],
    "asteroid": ["Solar system astronomy"],
    "microlensing": ["Gravitational lensing"],
}


def guess_uat_keywords(title, description, primary_recipient):
    text = f"{title or ''} {description or ''}".lower()
    pr = (primary_recipient or "").lower()
    tags = set()
    for key, vals in RECIPIENT_KEYWORDS.items():
        if key in pr:
            tags.update(vals)
    for key, vals in TEXT_KEYWORDS.items():
        if key in text:
            tags.update(vals)
    if not tags:
        tags.add("Astronomy software")
    return sorted(tags)


def normalize_ws(value):
    if value is None:
        return None
    cleaned = " ".join(value.replace("\xa0", " ").split())
    return cleaned or None


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def split_list(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


# --- read the proposal-spreadsheet CSV ----------------------------------
# Covers both Software and Datasets contributions (General Pool is skipped).
# Optional -- see module docstring. Returns {} if no path is given.

def load_contributions(path):
    if path is None:
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[2]
    assert header[2] == "ID", f"unexpected header row: {header}"
    records = {}
    for row in rows[3:]:
        if not row[2].strip():
            continue
        category_code = row[7].strip().split(" ", 1)[0]
        if category_code == "4.1":
            continue  # General Pool -- has its own page, not imported here
        recipients = [r.strip() for r in row[8].split(",") if r.strip()]
        primary = row[9].strip()
        additional = [r for r in recipients if r != primary]
        cid = row[2].strip()
        records[cid] = {
            "contribution_id": cid,
            "title": normalize_ws(row[3]),
            "country": row[0].strip(),
            "institute": row[1].strip(),
            "category_code": category_code,
            "category": CATEGORY_LABELS.get(category_code, row[7].strip()),
            "primary_recipient_group": primary,
            "additional_recipient_groups": additional,
            "activity_description": normalize_ws(row[10]),
            # Free-text FTE-by-fiscal-year narrative, not a clean date --
            # the page derives a rough "first FY mentioned" indicator from
            # this, see conf.py's _approx_start_fy().
            "timeline": normalize_ws(row[6]),
        }
    return records


# --- read the shared Google Form export ---------------------------------
#
# The form asks "Maintenance Plan & Updates" and "Describe any planned
# updates or maintenance" TWICE -- once for the software section (columns
# 17-18) and again for the dataset section (columns 34-35). csv.DictReader
# keys rows by header name, so it silently collapses each duplicate pair to
# whichever column comes last, which quietly overwrote the software-specific
# answer with the dataset one. Reading by fixed position instead of by
# header name sidesteps that entirely.
FORM_COLUMNS = [
    "timestamp", "email", "contribution_id", "submitter_name", "target_audience",
    "software_name", "contribution_summary", "version", "deliverable_type",
    "software_url", "documentation", "verification_testing", "sharing_of_software",
    "publications", "acknowledgements", "support",
    "sw_maintenance_plan", "sw_maintenance_notes", "further_development", "other_feedback",
    "data_products_expected", "data_type", "data_volume", "data_schema_link",
    "hosting_location", "access_url", "access_mechanisms", "authentication",
    "generation_methods", "validation_limitations", "tutorials_docs", "support_channel",
    "citation", "ds_maintenance_plan", "ds_maintenance_notes", "final_report",
    "uat_category", "uat_concepts",
]


def load_form_responses(path):
    """Return (software_responses, dataset_responses, software_ids, dataset_ids):
    the latest response per Contribution ID, split by the row's own
    "Contribution deliverable type" answer, plus the ID sets for each
    (used for the unmatched-ID warnings in sync())."""
    if path is None:
        return {}, {}, set(), set()
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    if len(header) != len(FORM_COLUMNS):
        raise ValueError(
            f"form CSV has {len(header)} columns, expected {len(FORM_COLUMNS)} -- "
            "the form likely changed; update FORM_COLUMNS to match before re-running."
        )
    software_responses, dataset_responses = {}, {}
    software_ids, dataset_ids = set(), set()
    for raw in rows[1:]:
        row = dict(zip(FORM_COLUMNS, raw))
        cid = row["contribution_id"].strip()
        if not cid:
            continue
        deliverable_type = row["deliverable_type"].strip()
        # Later rows (later timestamps) win if a team resubmits, or edits
        # their response in place and the export is re-pulled.
        if deliverable_type == "Software":
            software_ids.add(cid)
            software_responses[cid] = row
        elif deliverable_type == "Datasets":
            dataset_ids.add(cid)
            dataset_responses[cid] = row
        # else: blank/unrecognized deliverable type -- skip silently, the
        # row is presumably incomplete (form still in progress).
    return software_responses, dataset_responses, software_ids, dataset_ids


DATASET_FIELD_MAP = {
    "data_type": "data_type",
    "data_volume": "data_volume",
    "data_schema_link": "data_schema_link",
    "hosting_location": "hosting_location",
    "access_url": "access_url",
    "access_mechanisms": "access_mechanisms",
    "authentication": "authentication",
    "generation_methods": "generation_methods",
    "validation_limitations": "validation_limitations",
    "tutorials_docs": "tutorials_docs",
    "support_channel": "support_channel",
    "citation": "citation",
    "ds_maintenance_plan": "maintenance_plan",
    "ds_maintenance_notes": "maintenance_notes",
    "final_report": "final_report",
}
LIST_VALUED_DATASET_FIELDS = {"data_type", "access_mechanisms"}

# UAT category/concepts (Section 5) are asked once per submission, not
# once per branch -- unlike email/name/target audience/summary (Section 1),
# which genuinely only make sense on the *parent* Software record for a
# Software submission (there's no separate submitter identity for the
# nested dataset). The Datasets page's own filters and badges read
# `uat_category` from each dataset record's *own* form_data though, so an
# associated_dataset block needs its own copy of this too -- without it, a
# companion card auto-drafted (or updated) from a Software submission's
# data-products answers silently shows no UAT badges and never matches the
# "Science case (UAT)" filter, even though the parent Software card's own
# card looks correct. See build_associated_dataset() below.
ASSOCIATED_DATASET_UAT_FIELD_MAP = {
    "uat_category": "uat_category",
    "uat_concepts": "uat_concepts",
}
ASSOCIATED_DATASET_FIELD_MAP = {**DATASET_FIELD_MAP, **ASSOCIATED_DATASET_UAT_FIELD_MAP}
ASSOCIATED_DATASET_LIST_FIELDS = LIST_VALUED_DATASET_FIELDS | {"uat_category"}

# A direct Datasets-branch submission also answers Section 1 (common
# fields: email, name, target audience, summary, version) for itself,
# since there's no separate Software record to hold them -- an
# associated_dataset drafted/updated from a *Software* submission
# deliberately omits these, since that submission's own top-level
# form_data already carries them for the whole contribution. See
# build_dataset_form_data() vs. build_associated_dataset() below.
DIRECT_DATASET_EXTRA_FIELD_MAP = {
    "email": "email",
    "submitter_name": "name",
    "target_audience": "target_audience",
    "contribution_summary": "contribution_summary",
    "version": "version",
    **ASSOCIATED_DATASET_UAT_FIELD_MAP,
}
DIRECT_DATASET_LIST_FIELDS = LIST_VALUED_DATASET_FIELDS | {"uat_category"}


def _dataset_fields_from_response(response, field_map, list_fields):
    out = {"submitted": True}
    for form_col, out_key in field_map.items():
        value = normalize_ws(response.get(form_col))
        out[out_key] = split_list(value) if out_key in list_fields else value
    return out


def build_associated_dataset(response):
    """The dataset block nested inside a *Software* record, only present
    when that submission answered "Yes" to expecting data products."""
    if normalize_ws(response.get("data_products_expected", "")) != "Yes":
        return None
    return _dataset_fields_from_response(
        response, ASSOCIATED_DATASET_FIELD_MAP, ASSOCIATED_DATASET_LIST_FIELDS
    )


def build_dataset_form_data(response):
    """form_data for a *direct* Datasets-branch submission (its own card,
    not nested under a software record)."""
    full_map = {**DATASET_FIELD_MAP, **DIRECT_DATASET_EXTRA_FIELD_MAP}
    return _dataset_fields_from_response(response, full_map, DIRECT_DATASET_LIST_FIELDS)


def merge_form_response(record, response):
    record["submitted"] = True
    record["email"] = normalize_ws(response.get("email"))
    record["submitter_name"] = normalize_ws(response.get("submitter_name"))
    record["target_audience"] = normalize_ws(response.get("target_audience"))
    record["software_name"] = normalize_ws(response.get("software_name"))
    record["version"] = normalize_ws(response.get("version"))
    record["software_url"] = normalize_ws(response.get("software_url"))
    record["documentation"] = normalize_ws(response.get("documentation"))
    record["verification_testing"] = normalize_ws(response.get("verification_testing"))
    record["sharing_of_software"] = normalize_ws(response.get("sharing_of_software"))
    record["publications"] = normalize_ws(response.get("publications"))
    record["acknowledgements"] = normalize_ws(response.get("acknowledgements"))
    record["support"] = normalize_ws(response.get("support"))
    record["maintenance_plan"] = normalize_ws(response.get("sw_maintenance_plan"))
    record["maintenance_notes"] = normalize_ws(response.get("sw_maintenance_notes"))
    record["further_development"] = normalize_ws(response.get("further_development"))
    record["other_feedback"] = normalize_ws(response.get("other_feedback"))
    uat_category = split_list(response.get("uat_category"))
    record["uat_category"] = uat_category or None
    record["uat_concepts"] = normalize_ws(response.get("uat_concepts"))
    record["associated_dataset"] = build_associated_dataset(response)


# --- cross-page relation lookup -----------------------------------------

def collect_existing_ids(data_dir):
    """Map contribution_id -> title for every record already on disk under
    a _data directory (contribution_id may be a scalar or a list, per the
    Telescopes page's multi-facility records)."""
    out = {}
    if not data_dir.exists():
        return out
    for path in sorted(data_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            rec = yaml.safe_load(f) or {}
        cid = rec.get("contribution_id")
        cids = cid if isinstance(cid, list) else [cid]
        for c in cids:
            if c:
                out[c] = rec.get("title") or rec.get("facility") or c
    return out


# --- review gate ----------------------------------------------------------
# Shared by both card types: an *existing* record's form_data is never
# overwritten silently. New fields (a first submission), changed fields (a
# resubmission, or a team editing their response in place without
# resubmitting), all go through the same before/after diff + prompt.

def diff_fields(old_data, new_data):
    old_data = old_data or {}
    return [k for k, new_v in new_data.items() if old_data.get(k) != new_v]


def _format_value(value):
    text = "(empty)" if value in (None, [], "") else str(value)
    return text if len(text) <= 100 else text[:97] + "..."


class ReviewState:
    def __init__(self, auto_yes=False):
        self.apply_all = auto_yes
        self.quit = False


def review_update(cid, title, changed_fields, old_data, new_data, state):
    """Print a before/after diff for `changed_fields` and ask whether to
    apply it. Returns True to apply, False to leave the file untouched."""
    if state.quit:
        return False
    if state.apply_all:
        return True
    print(f"\n--- update available: {cid} -- {title} ---")
    for field in changed_fields:
        print(f"  {field}:")
        print(f"    was: {_format_value((old_data or {}).get(field))}")
        print(f"    now: {_format_value(new_data.get(field))}")
    while True:
        choice = input(
            "Apply this update? [y]es / [n]o (default) / [a]ll remaining / [q]uit remaining: "
        ).strip().lower()
        if choice in ("", "n", "no"):
            return False
        if choice in ("y", "yes"):
            return True
        if choice in ("a", "all"):
            state.apply_all = True
            return True
        if choice in ("q", "quit"):
            state.quit = True
            return False
        print("Please enter y, n, a, or q.")


# --- YAML record assembly ------------------------------------------------

SPREADSHEET_ONLY_FIELDS = (
    "category", "primary_recipient_group", "additional_recipient_groups",
    "activity_description", "timeline",
)


def default_software_form_data(contrib, existing_form_data=None):
    """contrib is the matching row from the (optional) --contributions
    spreadsheet, or None if there isn't one -- e.g. every ongoing run now
    that the spreadsheet isn't being re-pulled. The form itself never
    supplies category/recipient-group/activity-description/timeline, so
    without a spreadsheet row this run, those fields fall back to whatever
    is already on disk (existing_form_data) rather than being blanked out."""
    contrib = contrib or {}
    existing_form_data = existing_form_data or {}
    spreadsheet_source = contrib if contrib else existing_form_data
    return {
        "category": spreadsheet_source.get("category"),
        "primary_recipient_group": spreadsheet_source.get("primary_recipient_group"),
        "additional_recipient_groups": spreadsheet_source.get("additional_recipient_groups") or [],
        "activity_description": spreadsheet_source.get("activity_description"),
        "timeline": spreadsheet_source.get("timeline"),
        "submitted": False,
        "email": None,
        "submitter_name": None,
        "target_audience": None,
        "software_name": None,
        "version": None,
        "software_url": None,
        "documentation": None,
        "verification_testing": None,
        "sharing_of_software": None,
        "publications": None,
        "acknowledgements": None,
        "support": None,
        "maintenance_plan": None,
        "maintenance_notes": None,
        "further_development": None,
        "other_feedback": None,
        "uat_category": None,
        "uat_concepts": None,
        "associated_dataset": None,
    }


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=88)


def write_dataset_yaml(path, data):
    """Same as write_yaml, but keeps the Datasets page's established
    form_data/curated header comments (yaml.safe_dump can't preserve
    comments through a full round-trip, so they're re-applied here)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = {k: data[k] for k in ("contribution_id", "title", "country", "institute")}
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(identity, f, sort_keys=False, allow_unicode=True, width=88)
        f.write("\n# --- fields the CSV pull script owns; safe to overwrite on every sync ---\n")
        yaml.safe_dump({"form_data": data["form_data"]}, f, sort_keys=False, allow_unicode=True, width=88)
        f.write("\n# --- fields only a human edits; the pull script never touches these ---\n")
        yaml.safe_dump({"curated": data["curated"]}, f, sort_keys=False, allow_unicode=True, width=88)


# --- software sync --------------------------------------------------------
# Driven by the union of (a) --contributions rows with a known software
# category code, if that optional spreadsheet was supplied, and (b) every
# ID with a Software-branch form response. (a) is the rare bulk/one-off
# path (still creates a "pending" placeholder for a contribution with no
# response yet); (b) is the ongoing day-to-day path -- a contribution with
# no spreadsheet row still gets synced, just with incomplete identity
# fields (title falls back to the form's own name field; country/institute/
# category/timeline/activity_description are left blank) and flagged
# needs_review so the coordinator can fill them in by hand.

def sync_associated_dataset(cid, title, country, institute, form_data, assoc, review_state):
    """Create or update the companion Datasets card for a Software
    submission that answered "Yes" to expecting data products.

    This updates an *existing* Datasets card too, not just a missing one --
    several of the original 16 dataset cards were backfilled as pre-
    delivery placeholders (guessed data type/UAT tags, `submitted: false`)
    before this script existed, for contributions whose data products were
    expected to arrive via a *Software* submission rather than a direct
    Datasets-branch response. Previously, once any Datasets card existed
    for an ID -- placeholder or not -- a Software submission's
    associated_dataset answers were captured into the Software record's
    own form_data.associated_dataset block and never propagated any
    further, leaving that Datasets card frozen at its placeholder content
    forever, even after the real data arrived. Routing every
    associated_dataset (not just ones with no existing card) through the
    same review-diff gate as everything else fixes that.

    Returns (outcome, changed_fields) where outcome is one of "created",
    "updated", "skipped", "unchanged".
    """
    out_path = DATASETS_DIR / f"{cid}.yaml"
    if out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}
        changed = diff_fields(existing.get("form_data"), assoc)
        if not changed:
            return "unchanged", None
        existing_title = existing.get("title") or title
        if not review_update(cid, existing_title, changed, existing.get("form_data"), assoc, review_state):
            return "skipped", None
        record = {
            "contribution_id": cid,
            # Title/country/institute protected once a Datasets record
            # exists, same as the direct-response sync path.
            "title": existing.get("title") or title,
            "country": existing.get("country") or country,
            "institute": existing.get("institute") or institute,
            "form_data": assoc,
            # curated is hand-edited only and never touched on update --
            # same convention as sync_datasets()'s existing-record branch.
            "curated": existing.get("curated") or {},
        }
        write_dataset_yaml(out_path, record)
        return "updated", changed
    else:
        draft = {
            "contribution_id": cid,
            "title": f"{title} (associated dataset)",
            "country": country,
            "institute": institute,
            "form_data": assoc,
            "curated": {
                "primary_recipient": form_data.get("primary_recipient_group"),
                "target_audience": form_data.get("target_audience"),
                "summary": None,
                "wavelength_regime": [],
                "status_override": None,
                "related_contribution_ids": [cid],
                "needs_review": True,
            },
        }
        write_dataset_yaml(out_path, draft)
        return "created", None


def sync_software(contributions, software_responses, review_state):
    SOFTWARE_DIR.mkdir(parents=True, exist_ok=True)
    dataset_titles = collect_existing_ids(DATASETS_DIR)
    telescope_titles = collect_existing_ids(TELESCOPES_DIR)

    created, updated, skipped, unchanged = [], [], [], []
    drafts_written, dataset_updates, dataset_skips = [], [], []
    dataset_touched_ids = set()

    # The spreadsheet also carries Datasets-category rows (Steve confirmed
    # both live in the same export) -- only known software category codes
    # are eligible here. A Datasets-category row is only ever handled by
    # sync_datasets().
    software_cids_from_sheet = {
        cid for cid, row in contributions.items() if row.get("category_code") in CATEGORY_LABELS
    }
    all_cids = sorted(software_cids_from_sheet | set(software_responses))

    for cid in all_cids:
        contrib = contributions.get(cid) if cid in software_cids_from_sheet else None

        out_path = SOFTWARE_DIR / f"{cid}.yaml"
        existing = None
        if out_path.exists():
            with out_path.open(encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}

        form_data = default_software_form_data(contrib, existing.get("form_data") if existing else None)
        response = software_responses.get(cid)
        if response:
            merge_form_response(form_data, response)

        assoc = form_data.get("associated_dataset")
        related = []
        if cid in dataset_titles or cid in telescope_titles or assoc:
            related.append(cid)

        # Identity fields (title/country/institute) are set once at
        # creation and protected after that -- from the spreadsheet if
        # available, else a fallback derived from the form response.
        title_fallback = normalize_ws(response.get("software_name")) if response else None
        if contrib:
            title = contrib["title"]
            country, institute = contrib["country"], contrib["institute"]
        elif existing:
            title = existing.get("title") or title_fallback or cid
            country, institute = existing.get("country"), existing.get("institute")
        else:
            title = title_fallback or cid
            country = institute = None

        if existing:
            changed = diff_fields(existing.get("form_data"), form_data)
            if not changed:
                unchanged.append(cid)
                continue
            if not review_update(cid, title, changed, existing.get("form_data"), form_data, review_state):
                skipped.append(cid)
                continue
            curated = existing.get("curated") or {
                "uat_keywords": guess_uat_keywords(
                    title, form_data.get("activity_description"), form_data.get("primary_recipient_group")
                ),
                "summary": None,
                "status_override": None,
                "related_contribution_ids": [],
            }
            # related_contribution_ids is the one field inside `curated`
            # that this script keeps auto-derived rather than hand-edited
            # only -- union in whatever's newly known (e.g. a companion
            # dataset that just got created or updated *this run*, for a
            # Software card that already existed before it) instead of
            # leaving it frozen at whatever it was when the card was first
            # created. Union, not replace, so a manually-added related ID
            # (e.g. a telescope) is never dropped.
            curated["related_contribution_ids"] = sorted(
                set(curated.get("related_contribution_ids") or []) | set(related)
            )
            updated.append((cid, changed))
        else:
            curated = {
                "uat_keywords": guess_uat_keywords(
                    title, form_data.get("activity_description"), form_data.get("primary_recipient_group")
                ),
                "summary": None,
                "status_override": None,
                "related_contribution_ids": related,
            }
            # A contribution with no spreadsheet row is missing
            # country/institute/category and needs a human pass, same
            # spirit as the Datasets page's needs_review flag.
            if not contrib:
                curated["needs_review"] = True
            created.append(cid)

        record = {
            "contribution_id": cid,
            "title": title,
            "country": country,
            "institute": institute,
            "form_data": form_data,
            "curated": curated,
        }
        write_yaml(out_path, record)

        # Create or update the companion Datasets record for a
        # contribution whose form response says data products are
        # expected -- see sync_associated_dataset() for why this also
        # covers a Datasets card that already existed (e.g. a pre-delivery
        # placeholder from the original backfill).
        if assoc:
            outcome, changed_fields = sync_associated_dataset(
                cid, title, country, institute, form_data, assoc, review_state
            )
            if outcome == "created":
                drafts_written.append(cid)
                dataset_touched_ids.add(cid)
            elif outcome == "updated":
                dataset_updates.append((cid, changed_fields))
                dataset_touched_ids.add(cid)
            elif outcome == "skipped":
                dataset_skips.append(cid)
            # "unchanged": nothing to report, file already matches.

    return {
        "created": created, "updated": updated, "skipped": skipped,
        "unchanged": unchanged, "drafts_written": drafts_written,
        "dataset_updates": dataset_updates, "dataset_skips": dataset_skips,
        "dataset_touched_ids": dataset_touched_ids,
    }


# --- direct datasets sync --------------------------------------------------
# Only touches a Datasets card when a *direct* Datasets-branch CSV response
# exists for that ID this run -- unlike software, there's no spreadsheet-
# driven placeholder pass, since we can't reliably tell a not-yet-submitted
# dataset contribution's category code apart from other categories in the
# proposal spreadsheet. Existing pre-delivery records with no response yet
# are simply left untouched, same as before this script existed.

def sync_datasets(contributions, dataset_responses, software_touched_ids, review_state):
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    created, updated, skipped, unchanged, conflicts = [], [], [], [], []

    for cid, response in sorted(dataset_responses.items()):
        if cid in software_touched_ids:
            conflicts.append(cid)  # see warning printed in sync()

        out_path = DATASETS_DIR / f"{cid}.yaml"
        new_form_data = build_dataset_form_data(response)
        title_from_response = normalize_ws(response.get("software_name")) or cid

        if out_path.exists():
            with out_path.open(encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
            changed = diff_fields(existing.get("form_data"), new_form_data)
            if not changed:
                unchanged.append(cid)
                continue
            title = existing.get("title") or title_from_response
            if not review_update(cid, title, changed, existing.get("form_data"), new_form_data, review_state):
                skipped.append(cid)
                continue
            record = {
                "contribution_id": cid,
                # Title/country/institute are protected once a Datasets
                # record exists -- largely hand-set during the original
                # page backfill, not spreadsheet/form-owned like software's.
                "title": existing.get("title") or title_from_response,
                "country": existing.get("country"),
                "institute": existing.get("institute"),
                "form_data": new_form_data,
                "curated": existing.get("curated") or {},
            }
            updated.append((cid, changed))
        else:
            contrib = contributions.get(cid)
            if contrib:
                title = contrib["title"]
                country = contrib["country"]
                institute = contrib["institute"]
                primary_recipient = contrib["primary_recipient_group"] or None
            else:
                title = title_from_response
                country = None
                institute = None
                primary_recipient = None
            record = {
                "contribution_id": cid,
                "title": title,
                "country": country,
                "institute": institute,
                "form_data": new_form_data,
                "curated": {
                    "primary_recipient": primary_recipient,
                    "target_audience": normalize_ws(response.get("target_audience")),
                    # Seeded from the submitter's own summary so there's a
                    # starting draft to fix spelling/tone on rather than a
                    # blank field -- never touched again after this.
                    "summary": normalize_ws(response.get("contribution_summary")),
                    "wavelength_regime": [],
                    "status_override": None,
                    "needs_review": True,
                },
            }
            created.append(cid)

        write_dataset_yaml(out_path, record)

    return {
        "created": created, "updated": updated, "skipped": skipped,
        "unchanged": unchanged, "conflicts": conflicts,
    }


def sync(contributions_csv, form_responses_csv, auto_yes):
    contributions = load_contributions(contributions_csv)
    software_responses, dataset_responses, software_ids, dataset_ids = (
        load_form_responses(form_responses_csv)
    )

    if contributions:
        unmatched_software = sorted(software_ids - set(contributions))
        if unmatched_software:
            print(f"NOTE: {len(unmatched_software)} Software-labeled form response(s) aren't in the "
                  f"proposal spreadsheet -- title/country/institute for new records will come from "
                  f"the form response itself and are flagged needs_review: {', '.join(unmatched_software)}")
        unmatched_datasets = sorted(dataset_ids - set(contributions))
        if unmatched_datasets:
            print(f"NOTE: {len(unmatched_datasets)} Datasets-labeled form response(s) aren't in the "
                  f"proposal spreadsheet -- title/country/institute for new records will come from "
                  f"the form response itself and are flagged needs_review: {', '.join(unmatched_datasets)}")

    review_state = ReviewState(auto_yes=auto_yes)

    sw_result = sync_software(contributions, software_responses, review_state)
    ds_result = sync_datasets(
        contributions, dataset_responses, sw_result["dataset_touched_ids"], review_state
    )

    for cid in ds_result["conflicts"]:
        print(f"WARNING: {cid} has both a Software-branch associated-dataset draft/update and a "
              f"direct Datasets-branch response this run -- the direct response takes precedence.")

    print("\n=== Software ===")
    print(f"{len(sw_result['created'])} new, {len(sw_result['updated'])} updated, "
          f"{len(sw_result['skipped'])} skipped (declined), {len(sw_result['unchanged'])} unchanged")
    if sw_result["created"]:
        print(f"  new: {', '.join(sw_result['created'])}")
    if sw_result["updated"]:
        for cid, changed in sw_result["updated"]:
            print(f"  updated {cid}: {', '.join(changed)}")
    if sw_result["drafts_written"]:
        print(f"  NEEDS-REVIEW: drafted {len(sw_result['drafts_written'])} companion dataset "
              f"record(s): {', '.join(sw_result['drafts_written'])}")
    if sw_result["dataset_updates"]:
        print(f"  companion dataset record(s) updated from a software submission's data-products "
              f"answers:")
        for cid, changed in sw_result["dataset_updates"]:
            print(f"    updated {cid}: {', '.join(changed)}")
    if sw_result["dataset_skips"]:
        print(f"  companion dataset update(s) declined: {', '.join(sw_result['dataset_skips'])}")

    print("\n=== Datasets ===")
    print(f"{len(ds_result['created'])} new, {len(ds_result['updated'])} updated, "
          f"{len(ds_result['skipped'])} skipped (declined), {len(ds_result['unchanged'])} unchanged")
    if ds_result["created"]:
        print(f"  NEEDS-REVIEW (new): {', '.join(ds_result['created'])}")
    if ds_result["updated"]:
        for cid, changed in ds_result["updated"]:
            print(f"  updated {cid}: {', '.join(changed)}")

    if review_state.quit:
        print("\nStopped early at your request -- any remaining un-reviewed changes were left untouched.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--form-responses", required=True, type=Path,
        help="The 'In-kind Contribution Resources' Google Form export CSV. "
             "This is the input for ongoing syncs.",
    )
    parser.add_argument(
        "--contributions", type=Path, default=None,
        help="OPTIONAL. The proposal-spreadsheet export CSV -- a one-off "
             "used to bulk-populate the initial set of cards. Not needed "
             "for ongoing syncs; see the module docstring.",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Apply every change without prompting (e.g. for a first bulk sync).",
    )
    args = parser.parse_args()
    sync(args.contributions, args.form_responses, args.yes)


if __name__ == "__main__":
    main()
