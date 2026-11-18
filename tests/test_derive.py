"""Direct tests for the small helpers in ``ikp_data.derive``."""

import datetime

import pytest

from ikp_data.derive import option_pairs, parse_date, slugify


def test_parse_date_returns_a_date_unchanged():
    assert parse_date(datetime.date(2027, 3, 15)) == datetime.date(2027, 3, 15)


def test_parse_date_reduces_a_datetime_to_its_date():
    # datetime is a subclass of date, so this pins the order of the checks:
    # a datetime must come back as a plain date, not as the datetime itself.
    result = parse_date(datetime.datetime(2027, 3, 15, 13, 45))
    assert result == datetime.date(2027, 3, 15)
    assert type(result) is datetime.date


def test_parse_date_reads_an_iso_string():
    assert parse_date("2027-03-15") == datetime.date(2027, 3, 15)


@pytest.mark.parametrize("unreadable", ["not a date", "2027-13-45", "", None, 20270315, 3.5])
def test_parse_date_treats_anything_unreadable_as_absent(unreadable):
    assert parse_date(unreadable) is None


def test_option_pairs_are_sorted_and_the_slug_is_the_slugified_label():
    pairs = option_pairs({"Radio", "Optical / IR", "X-ray"})
    assert pairs == [("Optical / IR", "optical-ir"), ("Radio", "radio"), ("X-ray", "x-ray")]
    assert all(slug == slugify(label) for label, slug in pairs)
