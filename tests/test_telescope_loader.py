"""Tests for required-field handling in the telescope loader.

A telescope record without a latitude must fail with an error that names the
file, not a bare KeyError/TypeError from deep inside the build. A record without
a longitude is allowed: it just gets no map marker.
"""

from pathlib import Path

import pytest
import yaml

from ikp_data.loaders.telescopes import _aperture_band, load_telescopes

# The invented fixture records (see tests/fixtures/README.md), so these tests do
# not depend on the real, changing card data.
FIXTURE_DATA_DIR = Path(__file__).resolve().parent / "fixtures" / "docs" / "contribution-types" / "_data"


def _data_dir_with_one_telescope(tmp_path, **overrides):
    """A temporary `_data` dir holding a copy of the fixture telescope record.

    Each keyword overrides (or, when the value is the string "DELETE", removes)
    a field of the copied record. Returns (data_dir, path_of_the_record).
    """
    source = sorted((FIXTURE_DATA_DIR / "telescopes").glob("*.yaml"))[0]
    record = yaml.safe_load(source.read_text(encoding="utf-8"))
    for key, value in overrides.items():
        if value == "DELETE":
            record.pop(key, None)
        else:
            record[key] = value
    (tmp_path / "telescopes").mkdir()
    target = tmp_path / "telescopes" / source.name
    target.write_text(yaml.safe_dump(record), encoding="utf-8")
    return tmp_path, target


def _load(data_dir):
    # A non-existent outline file is fine here: the map outline is then empty.
    return load_telescopes(data_dir, data_dir / "no-such-outline.svg")


@pytest.mark.parametrize("latitude", ["DELETE", None])
def test_missing_or_null_latitude_raises_value_error_naming_the_file(tmp_path, latitude):
    data_dir, path = _data_dir_with_one_telescope(tmp_path, latitude=latitude)
    with pytest.raises(ValueError, match="missing required field 'latitude'") as error:
        _load(data_dir)
    assert str(path) in str(error.value)


def test_missing_longitude_means_no_map_marker(tmp_path):
    data_dir, _ = _data_dir_with_one_telescope(tmp_path, longitude="DELETE")
    (record,) = _load(data_dir)["telescopes"]
    assert "marker_x" not in record


def test_complete_record_gets_a_map_marker(tmp_path):
    data_dir, _ = _data_dir_with_one_telescope(tmp_path)
    (record,) = _load(data_dir)["telescopes"]
    assert "marker_x" in record and "marker_y" in record


def test_aperture_value_is_the_largest_metre_value_or_none(tmp_path):
    data_dir, _ = _data_dir_with_one_telescope(tmp_path, aperture="2 x 8.4m")
    assert _load(data_dir)["telescopes"][0]["aperture_value"] == 8.4

    other = tmp_path / "other"
    other.mkdir()
    data_dir, _ = _data_dir_with_one_telescope(other, aperture="DELETE")
    assert _load(data_dir)["telescopes"][0]["aperture_value"] is None


def test_filter_and_sort_read_the_aperture_with_one_rule(tmp_path):
    # "12 x 1m" is a 1 m facility: small in the filter and 1 in the sort. The bare 12
    # is a count, not a size, so it must not make the facility "large".
    data_dir, _ = _data_dir_with_one_telescope(tmp_path, aperture="12 x 1m")
    record = _load(data_dir)["telescopes"][0]
    assert record["aperture_band"] == "small"
    assert record["aperture_value"] == 1


def test_aperture_with_no_metre_value_has_no_band():
    assert _aperture_band("TBD") is None
    assert _aperture_band("") is None
    assert _aperture_band(None) is None


def test_live_aperture_values_keep_their_bands():
    expected = {
        "1.0m": "small",
        "1.4m": "small",
        "1.5m / 1.0m": "small",
        "1.6m": "small",
        "1.8m": "small",
        "1.9m-1.0m": "small",
        "2m": "medium",
        "2.56m": "medium",
        "2.6m": "medium",
        "2 x 8.4m": "large",
        "8.2m": "large",
        "9.2m": "large",
        "10.4m": "large",
    }
    for aperture, band in expected.items():
        assert _aperture_band(aperture) == band, aperture
