"""Checks that look across records, which a per-file schema cannot do.

Why this file exists
--------------------
``ikp_data.schemas`` validates one record at a time. Some mistakes are only
visible when records are compared with each other:

* two datasets using the same contribution ID;
* a "related contribution" that points at an ID that does not exist, or (on a
  dataset or software record) at a telescope instead of a dataset or software record;
* a dataset (or software) record whose related IDs name only itself, with no software
  (or dataset) record of the same ID to link to;
* sibling facilities that are meant to be described identically but have drifted;
* an opportunity whose ``id`` differs from its file name;
* an opportunity whose milestones are in an impossible order (results announced
  before the deadline).

Each check returns ``Problem`` objects instead of raising, so the validator can
report every problem in one run. Checks work on the *raw* YAML dictionaries and
tolerate odd shapes (a missing key, a wrong type): reporting such a record is the
schema's job, and a check should simply skip what it cannot interpret.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Literal

from ikp_data.derive import SIBLING_CONSISTENCY_FIELDS, slugify

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Problem:
    """One finding from validation or a check."""

    severity: Severity
    file: str  # path relative to the data folder, e.g. "datasets/CHL-UCH-D1.yaml"
    message: str


@dataclass(frozen=True)
class RecordFile:
    """A YAML file that was loaded, ready for cross-record checks."""

    record_type: str  # folder name: telescopes, opportunities, datasets, software, idacs
    file: str  # path relative to the data folder
    data: Any  # whatever yaml.safe_load returned (normally a dict)


def _records_of(records: Iterable[RecordFile], record_type: str) -> list[RecordFile]:
    """Only the records of one type whose content is a mapping."""
    return [r for r in records if r.record_type == record_type and isinstance(r.data, dict)]


def _contribution_ids(data: dict) -> list[str]:
    """A record's contribution IDs as a list (telescopes may hold one ID or a list)."""
    value = data.get("contribution_id")
    values = value if isinstance(value, list) else [value]
    return [v for v in values if isinstance(v, str) and v]


# ---------------------------------------------------------------------------
# 1. Unique identifiers
# ---------------------------------------------------------------------------


def check_unique_ids(records: list[RecordFile]) -> list[Problem]:
    """Datasets and software need unique contribution IDs; other types need unique slugs.

    Telescopes are different on purpose: sibling facilities (for example the three
    KMTNet sites) share one contribution ID. What must be unique for a telescope
    is its *slug* (the file name, lowercased and cleaned), because the slug is the
    page anchor that links point at.
    """
    problems: list[Problem] = []

    # Datasets and software: the contribution ID identifies the card.
    for record_type in ("datasets", "software"):
        seen: dict[str, str] = {}
        for record in _records_of(records, record_type):
            for cid in _contribution_ids(record.data):
                if cid in seen:
                    problems.append(
                        Problem(
                            "error",
                            record.file,
                            f"contribution_id '{cid}' is already used by {seen[cid]}",
                        )
                    )
                else:
                    seen[cid] = record.file

    # Telescopes: unique slug from the file name (ikp_data.loaders: slugify(path.stem)).
    # Opportunities use the file name as the slug too. IDACs use the "slug" key.
    def stem(file: str) -> str:
        return file.rsplit("/", 1)[-1].removesuffix(".yaml")

    slug_sources = {
        "telescopes": lambda r: slugify(stem(r.file)),
        "opportunities": lambda r: slugify(stem(r.file)),
        "idacs": lambda r: slugify(str(r.data.get("slug") or stem(r.file))),
    }
    for record_type, slug_of in slug_sources.items():
        seen_slugs: dict[str, str] = {}
        for record in _records_of(records, record_type):
            slug = slug_of(record)
            if slug in seen_slugs:
                problems.append(
                    Problem(
                        "error",
                        record.file,
                        f"slug '{slug}' is already used by {seen_slugs[slug]} "
                        "(page anchors must be unique)",
                    )
                )
            else:
                seen_slugs[slug] = record.file

    # Opportunity ids should be unique as well (they name the opportunity).
    seen_ids: dict[str, str] = {}
    for record in _records_of(records, "opportunities"):
        opp_id = record.data.get("id")
        if isinstance(opp_id, str):
            if opp_id in seen_ids:
                problems.append(
                    Problem(
                        "error",
                        record.file,
                        f"id '{opp_id}' is already used by {seen_ids[opp_id]}",
                    )
                )
            else:
                seen_ids[opp_id] = record.file
    return problems


# ---------------------------------------------------------------------------
# 2. Cross-references
# ---------------------------------------------------------------------------


def _known_contribution_ids(records: list[RecordFile]) -> set[str]:
    """Every contribution ID defined by a telescope, dataset or software record."""
    known: set[str] = set()
    for record_type in ("telescopes", "datasets", "software"):
        for record in _records_of(records, record_type):
            known.update(_contribution_ids(record.data))
    return known


def check_related_ids_resolve(records: list[RecordFile]) -> list[Problem]:
    """Every ``related_contribution_ids`` entry must name a contribution that exists.

    A dangling ID silently drops its "Also see" link (or facility link) from the
    page, so it is reported as an error.
    """
    known = _known_contribution_ids(records)
    problems: list[Problem] = []

    def check(record: RecordFile, related: Any, where: str) -> None:
        if not isinstance(related, list):
            return
        for rid in related:
            if rid not in known:
                problems.append(
                    Problem(
                        "error",
                        record.file,
                        f"{where} contains '{rid}', which is not the contribution_id "
                        "of any telescope, dataset or software record",
                    )
                )

    for record_type in ("datasets", "software"):
        for record in _records_of(records, record_type):
            curated = record.data.get("curated")
            if isinstance(curated, dict):
                check(record, curated.get("related_contribution_ids"), "curated.related_contribution_ids")
    for record in _records_of(records, "opportunities"):
        check(record, record.data.get("related_contribution_ids"), "related_contribution_ids")
    return problems


def check_related_ids_are_datasets_or_software(records: list[RecordFile]) -> list[Problem]:
    """A dataset's or software record's related IDs may name only datasets or software.

    The "Also see" links on those two pages are built to point at other dataset
    and software cards. An ID that resolves to a telescope
    would have no sensible link target, so it is reported as an error. IDs that
    resolve to nothing at all are reported by ``check_related_ids_resolve``.
    """
    allowed: set[str] = set()
    for record_type in ("datasets", "software"):
        for record in _records_of(records, record_type):
            allowed.update(_contribution_ids(record.data))
    everything = _known_contribution_ids(records)

    problems: list[Problem] = []
    for record_type in ("datasets", "software"):
        for record in _records_of(records, record_type):
            curated = record.data.get("curated")
            related = curated.get("related_contribution_ids") if isinstance(curated, dict) else None
            if not isinstance(related, list):
                continue
            for rid in related:
                # Unknown IDs are the other check's job; here only wrong-type IDs.
                if rid in everything and rid not in allowed:
                    problems.append(
                        Problem(
                            "error",
                            record.file,
                            f"curated.related_contribution_ids contains '{rid}', which is a "
                            "telescope record; related IDs on dataset and software records "
                            "must name a dataset or software record",
                        )
                    )
    return problems


# ---------------------------------------------------------------------------
# 3. Sibling telescopes
# ---------------------------------------------------------------------------


def check_telescope_siblings(records: list[RecordFile]) -> list[Problem]:
    """Warn when copies of the *same* facility disagree on shared fields.

    This is the only place the drift is reported (the telescope loader does
    not check it). Siblings with different facility
    names (for example VST and LBT, contributed together for funding reasons) are
    expected to differ and are skipped. This is only a warning because a
    difference can be intentional.
    """
    groups: dict[str, list[RecordFile]] = defaultdict(list)
    for record in _records_of(records, "telescopes"):
        for cid in _contribution_ids(record.data):
            groups[cid].append(record)

    problems: list[Problem] = []
    for cid, group in groups.items():
        if len(group) < 2:
            continue
        if len({r.data.get("facility") for r in group}) > 1:
            continue  # different facilities sharing an ID: differences are expected
        for field in SIBLING_CONSISTENCY_FIELDS:
            values = {repr(r.data.get(field)) for r in group}
            if len(values) > 1:
                # One warning per group and field, attached to the first file.
                files = ", ".join(r.file for r in group)
                problems.append(
                    Problem(
                        "warning",
                        group[0].file,
                        f"sibling records under contribution_id '{cid}' disagree "
                        f"on '{field}' (files: {files})",
                    )
                )
    return problems


# ---------------------------------------------------------------------------
# 4. Opportunity milestone order
# ---------------------------------------------------------------------------


def _as_date(value: Any) -> datetime.date | None:
    """Interpret a milestone date (ISO string or date); None if it cannot be read."""
    if isinstance(value, datetime.datetime):
        return None
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def check_milestone_order(file: str, data: Any) -> list[Problem]:
    """Check the order of the dated roles inside one opportunity record.

    Rules:
    * ``results`` must be strictly later than the last ``deadline``.
    * ``next`` must be strictly later than ``results`` if there is one,
      otherwise strictly later than the last ``deadline``.

    Milestones without a role, or without a readable date, are ignored here
    (the schema reports unreadable dates).
    """
    if not isinstance(data, dict) or not isinstance(data.get("milestones"), list):
        return []

    dated_by_role: dict[str, list[tuple[datetime.date, str]]] = defaultdict(list)
    for milestone in data["milestones"]:
        if not isinstance(milestone, dict):
            continue
        role = milestone.get("role")
        date = _as_date(milestone.get("date"))
        if role and date:
            dated_by_role[role].append((date, str(milestone.get("label", ""))))

    problems: list[Problem] = []
    last_deadline = max(dated_by_role["deadline"], default=None)
    results = max(dated_by_role["results"], default=None)

    if results and last_deadline and results[0] <= last_deadline[0]:
        problems.append(
            Problem(
                "error",
                file,
                f"milestone '{results[1]}' (role results, {results[0]}) must be after the "
                f"last deadline '{last_deadline[1]}' ({last_deadline[0]})",
            )
        )

    # "next" is compared with results when present, otherwise with the last deadline.
    anchor, anchor_name = (results, "results") if results else (last_deadline, "last deadline")
    for next_date, next_label in dated_by_role["next"]:
        if anchor and next_date <= anchor[0]:
            problems.append(
                Problem(
                    "error",
                    file,
                    f"milestone '{next_label}' (role next, {next_date}) must be after the "
                    f"{anchor_name} '{anchor[1]}' ({anchor[0]})",
                )
            )
    return problems


def check_opportunity_milestones(records: list[RecordFile]) -> list[Problem]:
    """Run ``check_milestone_order`` on every opportunity record."""
    problems: list[Problem] = []
    for record in _records_of(records, "opportunities"):
        problems.extend(check_milestone_order(record.file, record.data))
    return problems


def check_opportunity_id_matches_file_name(records: list[RecordFile]) -> list[Problem]:
    """An opportunity's ``id`` must equal its file name without ``.yaml``.

    The schema describes ``id`` as matching the file name, and the page uses the
    file name as the banner anchor, so a mismatch would leave two different
    names for one opportunity.
    """
    problems: list[Problem] = []
    for record in _records_of(records, "opportunities"):
        opp_id = record.data.get("id")
        if not isinstance(opp_id, str):
            continue  # a missing or wrong-type id is reported by the schema
        file_stem = record.file.rsplit("/", 1)[-1].removesuffix(".yaml")
        if opp_id != file_stem:
            problems.append(
                Problem(
                    "error",
                    record.file,
                    f"id '{opp_id}' must equal the file name '{file_stem}' "
                    "(rename the file or change the id)",
                )
            )
    return problems


def check_related_id_is_not_only_the_record_itself(records: list[RecordFile]) -> list[Problem]:
    """A related ID equal to the record's own ID needs a twin of the other type.

    One contribution can deliver both a dataset and a software item, with the same
    ``contribution_id``. A dataset that lists its own ID links to that software
    item (and the reverse). If there is no such twin, the ID names only the record
    itself; a card never links to itself, so no "Also see" link would be shown.
    That is reported as an error.
    """
    # record type -> (the type that must hold the twin, how to name that type)
    twin_of = {"datasets": ("software", "software"), "software": ("datasets", "dataset")}
    ids_by_type = {
        record_type: {cid for r in _records_of(records, record_type) for cid in _contribution_ids(r.data)}
        for record_type in twin_of
    }

    problems: list[Problem] = []
    for record_type, (twin_type, twin_name) in twin_of.items():
        for record in _records_of(records, record_type):
            curated = record.data.get("curated")
            related = curated.get("related_contribution_ids") if isinstance(curated, dict) else None
            if not isinstance(related, list):
                continue
            own_ids = set(_contribution_ids(record.data))
            for rid in related:
                if rid in own_ids and rid not in ids_by_type[twin_type]:
                    problems.append(
                        Problem(
                            "error",
                            record.file,
                            f"curated.related_contribution_ids contains '{rid}', which names only "
                            f"this record itself (there is no {twin_name} record with that ID), "
                            "so no 'Also see' link would be shown",
                        )
                    )
    return problems


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_all_checks(records: list[RecordFile]) -> list[Problem]:
    """Run every cross-record check and return the combined list of problems."""
    problems: list[Problem] = []
    problems.extend(check_unique_ids(records))
    problems.extend(check_related_ids_resolve(records))
    problems.extend(check_related_ids_are_datasets_or_software(records))
    problems.extend(check_related_id_is_not_only_the_record_itself(records))
    problems.extend(check_telescope_siblings(records))
    problems.extend(check_opportunity_milestones(records))
    problems.extend(check_opportunity_id_matches_file_name(records))
    return problems
