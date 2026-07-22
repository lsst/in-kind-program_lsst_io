#!/usr/bin/env python3
"""Sync docs/contribution-types/_data/software/*.yaml from source CSVs.

Two inputs:
  --contributions   the proposal-spreadsheet export (one row per contribution;
                     columns: Country, Institute, ID, Contribution Title,
                     Scraped Recipient Group, SOW, Timeline, Category,
                     Recipient Group(s), Primary Recipient Group,
                     Activity Description). Timeline is a free-text
                     FTE-by-fiscal-year narrative, not a clean date -- it's
                     carried through as-is and the page derives a rough
                     "first FY mentioned" indicator from it.
  --form-responses  the "In-kind Contribution Resources" Google Form export,
                     shared with the Datasets page's intake. Only rows whose
                     "Contribution deliverable type" is Software are used
                     here; rows also answering "Yes" to data products get an
                     `associated_dataset` block and, if no Datasets record
                     exists yet for that ID, a draft one is written too.

Safe to re-run: `form_data` is fully regenerated every run (it's owned by
this script); `curated` is written once on first creation and never touched
again on subsequent runs, exactly like the Datasets page's own split.

General Pool contributions (Category "4.1 - General pooled SW dev") are
skipped entirely -- those already have their own page.
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

# --- UAT keyword guesser -----------------------------------------------
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
    text = f"{title} {description}".lower()
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


# --- read the proposal-spreadsheet CSV ----------------------------------

def load_contributions(path):
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
    """Return the latest Software-deliverable response per Contribution ID,
    plus the set of Contribution IDs among *those Software-labeled* responses
    (for the unmatched-response warning in sync() -- Datasets-labeled
    responses are a different page's concern and are never expected to
    appear in this spreadsheet, so they're excluded from that check)."""
    if path is None:
        return {}, set()
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    if len(header) != len(FORM_COLUMNS):
        raise ValueError(
            f"form CSV has {len(header)} columns, expected {len(FORM_COLUMNS)} -- "
            "the form likely changed; update FORM_COLUMNS to match before re-running."
        )
    responses = {}
    software_ids = set()
    for raw in rows[1:]:
        row = dict(zip(FORM_COLUMNS, raw))
        cid = row["contribution_id"].strip()
        if not cid or row["deliverable_type"].strip() != "Software":
            continue
        software_ids.add(cid)
        # Later rows (later timestamps) win if a team resubmits.
        responses[cid] = row
    return responses, software_ids


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


def split_list(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def build_associated_dataset(response):
    if normalize_ws(response.get("data_products_expected", "")) != "Yes":
        return None
    out = {"submitted": True}
    for form_col, out_key in DATASET_FIELD_MAP.items():
        value = normalize_ws(response.get(form_col))
        if out_key in LIST_VALUED_DATASET_FIELDS:
            out[out_key] = split_list(value)
        else:
            out[out_key] = value
    return out


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


# --- YAML record assembly ------------------------------------------------

def default_form_data(row):
    return {
        "category": row["category"],
        "primary_recipient_group": row["primary_recipient_group"],
        "additional_recipient_groups": row["additional_recipient_groups"],
        "activity_description": row["activity_description"],
        "timeline": row["timeline"],
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


def sync(contributions_csv, form_responses_csv):
    SOFTWARE_DIR.mkdir(parents=True, exist_ok=True)
    contributions = load_contributions(contributions_csv)
    form_responses, form_response_ids = load_form_responses(form_responses_csv)

    unmatched = sorted(form_response_ids - set(contributions))
    if unmatched:
        print(f"WARNING: {len(unmatched)} Software-labeled form response(s) reference a "
              f"Contribution ID not found in the spreadsheet (typo, or a General Pool "
              f"contribution that's out of scope here) -- skipped: {', '.join(unmatched)}")

    dataset_titles = collect_existing_ids(DATASETS_DIR)
    telescope_titles = collect_existing_ids(TELESCOPES_DIR)
    known_dataset_ids = set(dataset_titles)

    created, updated, drafts_written = [], [], []

    for cid, row in sorted(contributions.items()):
        form_data = default_form_data(row)
        response = form_responses.get(cid)
        if response:
            merge_form_response(form_data, response)

        assoc = form_data.get("associated_dataset")
        will_draft_dataset = bool(assoc) and cid not in known_dataset_ids
        related = []
        if cid in dataset_titles or cid in telescope_titles or will_draft_dataset:
            related.append(cid)

        out_path = SOFTWARE_DIR / f"{cid}.yaml"
        existing = None
        if out_path.exists():
            with out_path.open(encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}

        record = {
            "contribution_id": cid,
            "title": row["title"],
            "country": row["country"],
            "institute": row["institute"],
            "form_data": form_data,
        }
        if existing and existing.get("curated"):
            record["curated"] = existing["curated"]
            (updated if existing else created).append(cid)
        else:
            record["curated"] = {
                "uat_keywords": guess_uat_keywords(
                    row["title"], row["activity_description"], row["primary_recipient_group"]
                ),
                "summary": None,
                "status_override": None,
                "related_contribution_ids": related,
            }
            created.append(cid)

        write_yaml(out_path, record)

        # Auto-draft a companion Datasets record when this contribution's
        # form response says data products are expected and no Datasets
        # record exists for this ID yet -- flagged for coordinator review.
        if will_draft_dataset:
            draft_path = DATASETS_DIR / f"{cid}.yaml"
            draft = {
                "contribution_id": cid,
                "title": f"{row['title']} (associated dataset)",
                "country": row["country"],
                "institute": row["institute"],
                "form_data": assoc,
                "curated": {
                    "primary_recipient": row["primary_recipient_group"],
                    "target_audience": form_data.get("target_audience"),
                    "summary": None,
                    "wavelength_regime": [],
                    "status_override": None,
                    "related_contribution_ids": [cid],
                    "needs_review": True,
                },
            }
            write_yaml(draft_path, draft)
            known_dataset_ids.add(cid)
            drafts_written.append(cid)

    print(f"{len(contributions)} software records processed "
          f"({len(created)} new/first-touch, {len(updated)} pre-existing curated preserved)")
    if drafts_written:
        print(f"NEEDS-REVIEW: drafted {len(drafts_written)} companion dataset "
              f"record(s), please review before merging: {', '.join(drafts_written)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contributions", required=True, type=Path)
    parser.add_argument("--form-responses", type=Path, default=None)
    args = parser.parse_args()
    sync(args.contributions, args.form_responses)


if __name__ == "__main__":
    main()
