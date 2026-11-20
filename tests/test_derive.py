"""Direct tests for the small helpers in ``ikp_data.derive``."""

import datetime
import json
import locale

import pytest

from ikp_data.derive import display_country, format_date, largest_metre_value, option_pairs, parse_date, search_index_to_json, slugify, sort_cards


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


# ---------------------------------------------------------------------------
# largest_metre_value: the number the Aperture column sorts by
# ---------------------------------------------------------------------------

# The distinct aperture strings on the live Telescope Access page, with the
# number each should sort as.
LIVE_APERTURES = [
    ("10.4m", 10.4),
    ("1.6m", 1.6),
    ("2 x 8.4m", 8.4),
    ("1.4m", 1.4),
    ("9.2m", 9.2),
    ("8.2m", 8.2),
    ("2.6m", 2.6),
    ("1.0m", 1.0),
    ("1.8m", 1.8),
    ("1.5m / 1.0m", 1.5),
    ("2m", 2.0),
    ("1.9m-1.0m", 1.9),
    ("2.56m", 2.56),
]


@pytest.mark.parametrize("text, expected", LIVE_APERTURES)
def test_largest_metre_value_reads_the_live_aperture_strings(text, expected):
    assert largest_metre_value(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2.4 m", 2.4),  # a space before the unit is fine
        ("0.5m, 3m", 3.0),  # the largest, not the first
        ("8.4m x 2", 8.4),  # a bare count is not a size
        ("10m (with 2m spare)", 10.0),
        # Not in the data, but pinned so a change is deliberate: a bare ".5m"
        # reads as 5, and a decimal comma ("8,4m") reads as 4.
        (".5m", 5.0),
        ("8,4m", 4.0),
    ],
)
def test_largest_metre_value_handles_other_layouts(text, expected):
    assert largest_metre_value(text) == expected


@pytest.mark.parametrize("text", [None, "", "TBA", "8", "2 x 8", "300mm", "4 meters"])
def test_largest_metre_value_is_none_without_a_size_in_metres(text):
    assert largest_metre_value(text) is None


# ---------------------------------------------------------------------------
# sort_cards: the order of the cards and table rows
# ---------------------------------------------------------------------------


def _card(contribution_id, status, last_updated):
    return {"contribution_id": contribution_id, "status": status, "last_updated": last_updated}


def test_sort_cards_puts_available_first_even_when_older():
    cards = [
        _card("AAA-S1", "pending", "2026-11-01"),
        _card("BBB-S1", "available", "2026-01-01"),
    ]
    assert [c["contribution_id"] for c in sort_cards(cards)] == ["BBB-S1", "AAA-S1"]


def test_sort_cards_orders_each_group_by_newest_date_then_contribution_id():
    cards = [
        _card("CCC-S1", "available", "2026-03-01"),
        _card("BBB-S2", "available", "2026-05-01"),
        _card("BBB-S1", "available", "2026-05-01"),
        _card("DDD-S1", "pending", "2026-06-01"),
        _card("AAA-S1", "pending", "2026-06-01"),
        _card("EEE-S1", "pending", "2026-02-01"),
    ]
    ordered = [c["contribution_id"] for c in sort_cards(cards)]
    assert ordered == ["BBB-S1", "BBB-S2", "CCC-S1", "AAA-S1", "DDD-S1", "EEE-S1"]


def test_sort_cards_does_not_change_the_list_it_is_given():
    cards = [_card("B", "pending", "2026-01-01"), _card("A", "available", "2026-01-01")]
    sort_cards(cards)
    assert [c["contribution_id"] for c in cards] == ["B", "A"]


def test_sort_cards_puts_a_record_without_a_date_last_in_its_status_group():
    cards = [
        _card("AAA-S1", "available", None),
        _card("BBB-S1", "available", "2026-01-01"),
        _card("CCC-S1", "pending", None),
        _card("DDD-S1", "pending", "2026-01-01"),
    ]
    ordered = [c["contribution_id"] for c in sort_cards(cards)]
    assert ordered == ["BBB-S1", "AAA-S1", "DDD-S1", "CCC-S1"]


def test_sort_cards_breaks_date_ties_in_natural_id_order():
    cards = [
        _card("ITA-INA-S10", "pending", "2026-07-22"),
        _card("ITA-INA-S2", "pending", "2026-07-22"),
        _card("ITA-INA-S1", "pending", "2026-07-22"),
        # A different prefix sorts by the prefix first, whatever the numbers are.
        _card("ESP-BCM-S12", "pending", "2026-07-22"),
        _card("ITA-OXF-S3", "pending", "2026-07-22"),
    ]
    ordered = [c["contribution_id"] for c in sort_cards(cards)]
    assert ordered == ["ESP-BCM-S12", "ITA-INA-S1", "ITA-INA-S2", "ITA-INA-S10", "ITA-OXF-S3"]


# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime.date(2026, 9, 30), "30 Sep 2026"),
        (datetime.date(2026, 9, 1), "1 Sep 2026"),  # no leading zero on the day
        ("2027-03-05", "5 Mar 2027"),  # an ISO string, as YAML gives for a quoted date
        (datetime.datetime(2026, 12, 31, 23, 59), "31 Dec 2026"),
        (datetime.date(2026, 5, 7), "7 May 2026"),
    ],
)
def test_format_date(value, expected):
    assert format_date(value) == expected


def test_format_date_names_all_twelve_months():
    months = [format_date(datetime.date(2026, m, 15)).split()[1] for m in range(1, 13)]
    assert months == ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def test_format_date_ignores_the_machine_locale():
    previous = locale.setlocale(locale.LC_TIME)
    try:
        try:
            locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
        except locale.Error:
            pytest.skip("German locale is not installed here")
        assert format_date(datetime.date(2026, 3, 5)) == "5 Mar 2026"
    finally:
        locale.setlocale(locale.LC_TIME, previous)


@pytest.mark.parametrize("value", [None, "", "soon", "2026-13-01", 20260930])
def test_format_date_returns_none_for_an_unreadable_date(value):
    assert format_date(value) is None
