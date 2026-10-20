"""Tests for required-field handling in the telescope loader.

A telescope record without a latitude must fail with an error that names the
file, not a bare KeyError/TypeError from deep inside the build. A record without
a longitude is allowed: it just gets no map marker.
"""

from pathlib import Path

import pytest
import yaml

from ikp_data.loaders.telescopes import load_telescopes

REAL_DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "contribution-types" / "_data"


def _data_dir_with_one_telescope(tmp_path, **overrides):
    """A temporary `_data` dir holding a copy of one real telescope record.

    Each keyword overrides (or, when the value is the string "DELETE", removes)
    a field of the copied record. Returns (data_dir, path_of_the_record).
    """
    source = sorted((REAL_DATA_DIR / "telescopes").glob("*.yaml"))[0]
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
