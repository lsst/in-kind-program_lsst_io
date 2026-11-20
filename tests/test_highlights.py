"""Tests for the highlights that feed the "Highlighted" teaser row.

The Datasets and Software loaders add a ``highlights`` list to their context:
the active ``curated.highlight`` entries, soonest-expiring first, at most three.
These tests check the rules on the fixture data at fixed dates, and the
ordering and the cap on small records written into a temporary folder (never
the live data).
"""

import datetime
from pathlib import Path

import pytest
import yaml

from ikp_data.derive import MAX_HIGHLIGHTS, active_highlights
from ikp_data.loaders import build_contexts

FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "docs" / "contribution-types" / "_data"

# Both fixture highlights are active on this date (see tests/fixtures/README.md).
BEFORE_BOTH = datetime.date(2027, 3, 15)
DATASET_UNTIL = datetime.date(2027, 4, 30)
SOFTWARE_UNTIL = datetime.date(2027, 5, 31)

# page context name -> (name of its list of records, folder of its records)
PAGES = {
    "contributed_datasets": "datasets",
    "contributed_software": "software",
}


def highlights_on(date, page):
    """The `highlights` list the loader builds for `page` (a context name)."""
    return build_contexts(FIXTURE_DATA_DIR, today=date)[page]["highlights"]


def test_the_fixture_highlights_before_either_ends():
    assert highlights_on(BEFORE_BOTH, "contributed_datasets") == [
        {
            "title": "Fixture Catalogue of Invented Sources (highlighted dataset)",
            "reason": "Newly delivered",
            "anchor": "ds-cid-tst-fix-s2",
        }
    ]
    assert highlights_on(BEFORE_BOTH, "contributed_software") == [
        {
            "title": "Fixture Pipeline (invented software)",
            "reason": "Widely used",
            "anchor": "sw-cid-tst-fix-s3",
        }
    ]


def test_a_highlight_is_still_active_on_its_until_day():
    assert len(highlights_on(DATASET_UNTIL, "contributed_datasets")) == 1
    assert len(highlights_on(SOFTWARE_UNTIL, "contributed_software")) == 1


def test_a_highlight_is_gone_the_day_after_its_until_day():
    one_day = datetime.timedelta(days=1)
    assert highlights_on(DATASET_UNTIL + one_day, "contributed_datasets") == []
    assert highlights_on(SOFTWARE_UNTIL + one_day, "contributed_software") == []


def test_each_page_expires_independently():
    # Between the two end dates only the Software row is left.
    between = DATASET_UNTIL + datetime.timedelta(days=1)
    assert highlights_on(between, "contributed_datasets") == []
    assert len(highlights_on(between, "contributed_software")) == 1


def write_record(data_dir, folder, contribution_id, until=None, title=None):
    """Write the smallest valid record into `folder`, highlighted if `until` is given."""
    curated = {}
    if until is not None:
        curated["highlight"] = {"reason": f"Reason for {contribution_id}", "until": until}
    record = {
        "contribution_id": contribution_id,
        "title": title or f"Title of {contribution_id}",
        "last_updated": "2027-03-01",
        "form_data": {},
        "curated": curated,
    }
    (data_dir / folder).mkdir(parents=True, exist_ok=True)
    (data_dir / folder / f"{contribution_id}.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")


@pytest.mark.parametrize("page, folder", PAGES.items())
def test_no_highlight_gives_an_empty_list(tmp_path, page, folder):
    write_record(tmp_path, folder, "TST-AAA-S1")
    assert build_contexts(tmp_path, today=BEFORE_BOTH)[page]["highlights"] == []


@pytest.mark.parametrize("page, folder", PAGES.items())
def test_highlights_are_ordered_by_until_then_by_natural_id(tmp_path, page, folder):
    write_record(tmp_path, folder, "TST-AAA-S10", until="2027-04-01")
    write_record(tmp_path, folder, "TST-AAA-S2", until="2027-04-01")
    write_record(tmp_path, folder, "TST-AAA-S1", until="2027-05-01")
    highlights = build_contexts(tmp_path, today=BEFORE_BOTH)[page]["highlights"]
    # Soonest end first; the tie on 2027-04-01 puts S2 before S10 (natural order).
    assert [h["title"] for h in highlights] == [
        "Title of TST-AAA-S2",
        "Title of TST-AAA-S10",
        "Title of TST-AAA-S1",
    ]


@pytest.mark.parametrize("page, folder", PAGES.items())
def test_highlights_are_capped_at_three_keeping_the_soonest_ending(tmp_path, page, folder):
    for number, until in enumerate(["2027-06-05", "2027-06-02", "2027-06-04", "2027-06-01", "2027-06-03"], 1):
        write_record(tmp_path, folder, f"TST-AAA-S{number}", until=until)
    highlights = build_contexts(tmp_path, today=BEFORE_BOTH)[page]["highlights"]
    assert MAX_HIGHLIGHTS == 3
    # S4 ends 06-01, S2 ends 06-02, S5 ends 06-03; the two that end later are dropped.
    assert [h["title"] for h in highlights] == ["Title of TST-AAA-S4", "Title of TST-AAA-S2", "Title of TST-AAA-S5"]


def test_an_expired_highlight_does_not_use_up_a_place_in_the_cap(tmp_path):
    write_record(tmp_path, "datasets", "TST-AAA-S1", until="2027-03-01")
    for number in range(2, 6):
        write_record(tmp_path, "datasets", f"TST-AAA-S{number}", until="2027-06-01")
    highlights = build_contexts(tmp_path, today=BEFORE_BOTH)["contributed_datasets"]["highlights"]
    assert [h["title"] for h in highlights] == [f"Title of TST-AAA-S{n}" for n in (2, 3, 4)]


def test_a_highlight_with_an_unreadable_date_is_skipped():
    records = [
        {
            "contribution_id": "TST-AAA-S1",
            "title": "Bad date",
            "anchor": "ds-cid-tst-aaa-s1",
            "curated": {"highlight": {"reason": "x", "until": "soon"}},
        }
    ]
    assert active_highlights(records, BEFORE_BOTH) == []


def test_a_null_reason_gives_an_empty_string_not_none():
    records = [
        {
            "contribution_id": "TST-AAA-S1",
            "title": "No reason",
            "anchor": "ds-cid-tst-aaa-s1",
            "curated": {"highlight": {"reason": None, "until": "2027-04-01"}},
        }
    ]
    assert active_highlights(records, BEFORE_BOTH)[0]["reason"] == ""


@pytest.mark.parametrize("malformed", ["Newly delivered", ["x"], 5])
def test_a_highlight_that_is_not_a_mapping_is_treated_as_absent(malformed):
    records = [
        {
            "contribution_id": "TST-AAA-S1",
            "title": "Malformed",
            "anchor": "ds-cid-tst-aaa-s1",
            "curated": {"highlight": malformed},
        }
    ]
    assert active_highlights(records, BEFORE_BOTH) == []
