"""Direct tests for the small helpers in ``ikp_data.derive``."""

import datetime
import json

import pytest

from ikp_data.derive import display_country, option_pairs, parse_date, search_index_to_json, slugify


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


# ---------------------------------------------------------------------------
# search_index_to_json: safe to embed in a <script> block
# ---------------------------------------------------------------------------
def test_search_index_to_json_escapes_less_than_and_round_trips():
    """A value holding "</script><b>" must not appear as raw text, yet parse back unchanged."""
    search_index = {"slug-a": "before </script><b>bold</b> after", "slug-b": "plain text"}
    text = search_index_to_json(search_index)
    assert "<" not in text  # nothing can close the surrounding <script> block
    assert "\\u003c/script" in text  # "<" is written as the JSON escape \u003c
    assert json.loads(text) == search_index  # the page script sees identical strings


# ---------------------------------------------------------------------------
# display_country: "UK" is spelled out, everything else is left alone
# ---------------------------------------------------------------------------
def test_display_country_spells_out_uk():
    assert display_country("UK") == "United Kingdom"


@pytest.mark.parametrize("country", ["United Kingdom", "Italy", "Examplia", "", None])
def test_display_country_leaves_other_values_unchanged(country):
    assert display_country(country) == country
