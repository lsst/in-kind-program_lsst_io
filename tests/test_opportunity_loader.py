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
from ikp_data.loaders.opportunities import load_opportunities, milestone_date_text, phase_status_line
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


# ---------------------------------------------------------------------------
# The status line at the top of each banner
# ---------------------------------------------------------------------------


def test_each_fixture_phase_has_its_status_line():
    banners = _banners(FIXTURE_TODAY)
    assert {slug: r["status_line"] for slug, r in banners.items()} == {
        "fixture-upcoming-call": "Opens 1 Apr 2027",
        "fixture-open-call": "Deadline 15 Apr 2027",
        "fixture-in-review-call": "Submissions closed; review in progress. Results expected 1 Apr 2027",
        # The closed fixture has no "next" milestone, so only "Closed" is left.
        "fixture-closed-call": "Closed",
    }


def _record(phase, milestones):
    return {"phase": phase, "milestones": milestones}


def test_closed_status_line_names_the_next_opportunity_as_written():
    record = _record(
        "closed",
        [{"date": "2027-03-01", "display_date": "March 2027", "role": "next"}],
    )
    assert phase_status_line(record) == "Closed. Next opportunity expected March 2027"


def test_closed_status_line_uses_the_earliest_next_milestone():
    record = _record(
        "closed",
        [{"date": "2027-09-01", "role": "next"}, {"date": "2027-03-01", "role": "next"}],
    )
    assert phase_status_line(record) == "Closed. Next opportunity expected 1 Mar 2027"


def test_open_status_line_shows_the_next_deadline_that_has_not_passed():
    deadlines = [
        {"date": "2026-10-01", "role": "deadline", "passed": False},
        {"date": "2026-08-07", "role": "deadline", "passed": True},
    ]
    assert phase_status_line(_record("open", deadlines)) == "Deadline 1 Oct 2026"
    # With neither passed, the earlier one is the next to meet.
    for deadline in deadlines:
        deadline["passed"] = False
    assert phase_status_line(_record("open", deadlines)) == "Deadline 7 Aug 2026"


TWO_DEADLINE_CALL = """\
title: Call with two deadlines
milestones:
- label: Letters of intent due
  date: '2026-08-07'
  role: deadline
- label: Full proposals due
  date: '2026-10-01'
  role: deadline
visible_until: '2026-10-01'
"""


def test_two_deadline_call_changes_its_line_when_the_first_deadline_passes(tmp_path):
    # A record of its own (shaped like a real two-deadline call), so the test
    # does not depend on a live record that is removed once it expires.
    (tmp_path / "opportunities").mkdir()
    (tmp_path / "opportunities" / "two-deadline-call.yaml").write_text(TWO_DEADLINE_CALL, encoding="utf-8")

    def line(iso):
        return load_opportunities(tmp_path, _day(iso))["opportunities"][0]["status_line"]

    assert line("2026-08-01") == "Deadline 7 Aug 2026"
    assert line("2026-08-07") == "Deadline 7 Aug 2026"  # the deadline day itself
    assert line("2026-08-15") == "Deadline 1 Oct 2026"


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("upcoming", ""),  # nothing to say without an opening date
        ("open", ""),  # nothing to say without a deadline
        ("in_review", "Submissions closed; review in progress"),  # no results date to add
        ("closed", "Closed"),
    ],
)
def test_missing_milestones_are_left_out_without_printing_none(phase, expected):
    line = phase_status_line(_record(phase, [{"date": "2026-09-01", "label": "Informational"}]))
    assert line == expected
    assert "None" not in line


def test_an_unknown_or_hidden_phase_has_no_status_line():
    assert phase_status_line(_record("hidden", [])) == ""
    assert phase_status_line({}) == ""
