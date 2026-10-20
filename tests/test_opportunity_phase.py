"""Unit tests for the opportunity lifecycle functions (pure, no files involved).

``opportunity_phase`` and ``milestone_passed`` live in
``ikp_data.loaders.opportunities``. These tests cover every phase, every rule for
incomplete records, and the boundary days. The boundary decision: each phase lasts
through its end date, inclusive (so the deadline day itself is still "open").
"""

import datetime

import pytest

from ikp_data.loaders.opportunities import milestone_passed, opportunity_phase


def _day(iso):
    return datetime.date.fromisoformat(iso)


def _record(opens=None, deadlines=(), results=None, visible_until="2026-12-31"):
    """An opportunity dictionary with the given dated roles (ISO strings)."""
    milestones = []
    if opens:
        milestones.append({"label": "Opens", "date": opens, "role": "opens"})
    for deadline in deadlines:
        milestones.append({"label": "Deadline", "date": deadline, "role": "deadline"})
    if results:
        milestones.append({"label": "Results", "date": results, "role": "results"})
    milestones.append({"label": "Next", "date": "2027-03-01", "role": "next"})
    record = {"id": "x", "milestones": milestones}
    if visible_until:
        record["visible_until"] = visible_until
    return record


FULL = _record(
    opens="2026-08-01", deadlines=["2026-09-01"], results="2026-10-01", visible_until="2026-11-01"
)


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        ("2026-07-31", "upcoming"),
        ("2026-08-01", "open"),  # the opens day itself is open
        ("2026-08-15", "open"),
        ("2026-09-01", "open"),  # the deadline day itself is still open
        ("2026-09-02", "in_review"),
        ("2026-10-01", "in_review"),  # the results day itself is still in review
        ("2026-10-02", "closed"),
        ("2026-11-01", "closed"),  # the visible_until day itself is still shown
        ("2026-11-02", "hidden"),
    ],
)
def test_full_record_phase_by_day(today, expected):
    assert opportunity_phase(FULL, _day(today)) == expected


def test_no_opens_is_never_upcoming():
    record = _record(deadlines=["2026-09-01"])
    assert opportunity_phase(record, _day("2000-01-01")) == "open"


def test_no_deadline_is_open_until_visible_until_then_hidden():
    record = _record(opens="2026-08-01", visible_until="2026-11-01")
    assert opportunity_phase(record, _day("2026-07-01")) == "upcoming"
    assert opportunity_phase(record, _day("2026-10-30")) == "open"
    assert opportunity_phase(record, _day("2026-11-01")) == "open"
    assert opportunity_phase(record, _day("2026-11-02")) == "hidden"


def test_no_deadline_ignores_results():
    record = _record(results="2026-10-01")
    assert opportunity_phase(record, _day("2026-10-15")) == "open"


def test_last_deadline_decides():
    record = _record(deadlines=["2026-08-07", "2026-10-01"])
    assert opportunity_phase(record, _day("2026-09-01")) == "open"  # past the first only
    assert opportunity_phase(record, _day("2026-10-01")) == "open"
    assert opportunity_phase(record, _day("2026-10-02")) == "closed"


def test_deadline_order_in_the_file_does_not_matter():
    record = _record(deadlines=["2026-10-01", "2026-08-07"])
    assert opportunity_phase(record, _day("2026-09-01")) == "open"


def test_no_results_goes_straight_from_open_to_closed():
    record = _record(deadlines=["2026-09-01"])
    assert opportunity_phase(record, _day("2026-09-01")) == "open"
    assert opportunity_phase(record, _day("2026-09-02")) == "closed"


def test_hidden_wins_over_every_other_phase():
    record = _record(opens="2026-08-01", visible_until="2026-07-01")  # odd, but explicit
    assert opportunity_phase(record, _day("2026-07-02")) == "hidden"


def test_missing_visible_until_is_never_hidden():
    record = _record(deadlines=["2026-09-01"], visible_until=None)
    assert opportunity_phase(record, _day("2099-01-01")) == "closed"


def test_milestones_without_a_role_or_date_are_ignored():
    record = {
        "visible_until": "2026-12-31",
        "milestones": [
            {"label": "Informational", "date": "2026-01-01"},
            {"label": "Undated deadline", "role": "deadline"},
        ],
    }
    assert opportunity_phase(record, _day("2026-06-01")) == "open"


def test_date_objects_work_as_well_as_strings():
    record = {
        "visible_until": _day("2026-12-31"),
        "milestones": [{"label": "d", "date": _day("2026-09-01"), "role": "deadline"}],
    }
    assert opportunity_phase(record, _day("2026-09-02")) == "closed"


def test_a_record_with_no_milestones_is_open_until_visible_until():
    record = {"visible_until": "2026-12-31"}
    assert opportunity_phase(record, _day("2026-06-01")) == "open"
    assert opportunity_phase(record, _day("2027-01-01")) == "hidden"


@pytest.mark.parametrize(
    ("milestone_date", "expected"),
    [("2026-09-14", True), ("2026-09-15", False), ("2026-09-16", False)],
)
def test_milestone_passed_boundary(milestone_date, expected):
    milestone = {"label": "m", "date": milestone_date}
    assert milestone_passed(milestone, _day("2026-09-15")) is expected


def test_milestone_without_a_readable_date_is_never_passed():
    assert milestone_passed({"label": "no date"}, _day("2026-09-15")) is False
    assert milestone_passed({"label": "bad", "date": "soon"}, _day("2026-09-15")) is False


def test_milestone_passed_accepts_date_objects():
    assert milestone_passed({"date": _day("2026-01-01")}, _day("2026-09-15")) is True
