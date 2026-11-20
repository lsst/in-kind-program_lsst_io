"""Tests for what the opportunities loader adds to each record.

The loader stores each opportunity's ``phase`` and each milestone's computed
``passed`` flag (the lifecycle rules themselves are tested in
``test_opportunity_phase.py``). These tests run the loader on the invented
fixture records at fixed dates, so every phase is covered:

* a golden snapshot of the whole context on the fixtures' design date;
* explicit checks of visibility, banner order and the ``passed`` flags;
* the boundary rule that a milestone dated today has not passed.

To update the golden file (intended, reviewed changes only):
    tox run -e test -- --update-snapshots
"""

import datetime
from pathlib import Path

import pytest

from ikp_data.loaders import build_contexts
from ikp_data.loaders.opportunities import milestone_date_text
from snapshot_helpers import SNAPSHOT_DIR, dump

FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "docs" / "contribution-types" / "_data"

# The date the fixtures are designed around: one record in each phase.
FIXTURE_TODAY = datetime.date(2027, 3, 15)


def _day(iso):
    return datetime.date.fromisoformat(iso)


def _banners(today):
    """The loader's banner records for `today`, keyed by file name."""
    contexts = build_contexts(FIXTURE_DATA_DIR, today=today)
    return {r["slug"]: r for r in contexts["contributed_opportunities"]["opportunities"]}


def test_fixture_banners_match_golden_snapshot(request):
    opportunities = build_contexts(FIXTURE_DATA_DIR, today=FIXTURE_TODAY)["contributed_opportunities"]
    actual = dump(opportunities["opportunities"])
    golden_path = SNAPSHOT_DIR / "fixture_opportunities.json"

    if request.config.getoption("--update-snapshots"):
        golden_path.write_text(actual, encoding="utf-8")
        return

    assert golden_path.exists(), f"{golden_path} is missing; create it with --update-snapshots."
    assert actual == golden_path.read_text(encoding="utf-8")


def test_each_phase_is_stored_and_hidden_records_are_left_out():
    banners = _banners(FIXTURE_TODAY)
    assert {slug: r["phase"] for slug, r in banners.items()} == {
        "fixture-upcoming-call": "upcoming",
        "fixture-open-call": "open",
        "fixture-in-review-call": "in_review",
        "fixture-closed-call": "closed",
    }
    assert "fixture-hidden-call" not in banners


def test_banners_are_sorted_soonest_next_milestone_first():
    order = list(_banners(FIXTURE_TODAY))
    # Next dated milestone on the fixture date: open 2027-04-15, upcoming 2027-04-01,
    # in review 2027-04-01 (results), closed none. Ties keep the file-name order.
    assert order == [
        "fixture-in-review-call",
        "fixture-upcoming-call",
        "fixture-open-call",
        "fixture-closed-call",
    ]


@pytest.mark.parametrize(
    ("slug", "expected_passed"),
    [
        ("fixture-upcoming-call", [False, False, False]),
        ("fixture-open-call", [True, False, False]),
        ("fixture-in-review-call", [True, True, False]),
        ("fixture-closed-call", [True, True, True]),
    ],
)
def test_milestones_are_marked_passed_by_date(slug, expected_passed):
    milestones = _banners(FIXTURE_TODAY)[slug]["milestones"]
    assert [m["passed"] for m in milestones] == expected_passed


def test_a_milestone_dated_today_is_not_passed():
    # The open fixture's call opens on 2027-03-01 and its deadline is 2027-04-15.
    on_the_day = _banners(_day("2027-04-15"))["fixture-open-call"]
    assert [m["passed"] for m in on_the_day["milestones"]] == [True, False, False]
    assert on_the_day["phase"] == "open"  # the deadline day itself is still open
    day_after = _banners(_day("2027-04-16"))["fixture-open-call"]
    assert [m["passed"] for m in day_after["milestones"]] == [True, True, False]
    assert day_after["phase"] == "in_review"


def test_the_visible_until_day_is_still_shown():
    # fixture-hidden-call is visible through 2027-03-01 (as "closed").
    assert _banners(_day("2027-03-01"))["fixture-hidden-call"]["phase"] == "closed"
    assert "fixture-hidden-call" not in _banners(_day("2027-03-02"))


# ---------------------------------------------------------------------------
# Dates as the banner shows them
# ---------------------------------------------------------------------------


def test_milestone_dates_are_formatted_for_readers():
    milestones = _banners(FIXTURE_TODAY)["fixture-open-call"]["milestones"]
    assert [m["date_text"] for m in milestones] == ["1 Mar 2027", "15 Apr 2027", "15 May 2027"]


def test_display_date_wins_over_the_formatted_date():
    assert milestone_date_text({"date": "2027-03-01", "display_date": "March 2027"}) == "March 2027"


def test_an_unreadable_date_is_shown_as_written():
    assert milestone_date_text({"date": "spring"}) == "spring"
    assert milestone_date_text({"label": "no date at all"}) == ""
