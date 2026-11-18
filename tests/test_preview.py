"""Tests for the local preview switches (ikp_data/preview.py)."""

import datetime

import pytest

from ikp_data.preview import PreviewOverrideError, resolve_preview_settings

REAL_TODAY = datetime.date(2026, 11, 18)


def _resolve(tmp_path, environ):
    default_dir = tmp_path / "default-data"
    return default_dir, resolve_preview_settings(environ, default_dir, REAL_TODAY)


def test_no_switches_means_no_override(tmp_path):
    default_dir, settings = _resolve(tmp_path, {})
    assert settings.data_dir == default_dir
    assert settings.today == REAL_TODAY
    assert settings.notice is None


def test_empty_switches_are_ignored(tmp_path):
    _, settings = _resolve(tmp_path, {"IKP_TODAY": "", "IKP_DATA_DIR": "  ", "CI": "true"})
    assert settings.notice is None


def test_today_switch_overrides_the_date_and_is_announced(tmp_path):
    default_dir, settings = _resolve(tmp_path, {"IKP_TODAY": "2027-03-15"})
    assert settings.today == datetime.date(2027, 3, 15)
    assert settings.data_dir == default_dir
    assert settings.notice == "IKP preview override: IKP_TODAY=2027-03-15"


@pytest.mark.parametrize("bad", ["15/03/2027", "2027-13-01", "tomorrow", "2027-3-5x"])
def test_bad_date_is_a_clear_error(tmp_path, bad):
    with pytest.raises(PreviewOverrideError, match="IKP_TODAY.*YYYY-MM-DD"):
        _resolve(tmp_path, {"IKP_TODAY": bad})


def test_data_dir_switch_overrides_the_folder_and_is_announced(tmp_path):
    other = tmp_path / "other-data"
    other.mkdir()
    _, settings = _resolve(tmp_path, {"IKP_DATA_DIR": str(other)})
    assert settings.data_dir == other.resolve()
    assert settings.today == REAL_TODAY
    assert settings.notice == f"IKP preview override: IKP_DATA_DIR={other.resolve()}"


def test_both_switches_give_one_notice_line(tmp_path):
    other = tmp_path / "other-data"
    other.mkdir()
    _, settings = _resolve(tmp_path, {"IKP_TODAY": "2027-03-15", "IKP_DATA_DIR": str(other)})
    assert settings.notice.count("\n") == 0
    assert "IKP_TODAY=2027-03-15" in settings.notice
    assert "IKP_DATA_DIR=" in settings.notice


def test_missing_data_dir_is_a_clear_error(tmp_path):
    with pytest.raises(PreviewOverrideError, match="IKP_DATA_DIR.*not an existing folder"):
        _resolve(tmp_path, {"IKP_DATA_DIR": str(tmp_path / "nope")})


@pytest.mark.parametrize("ci_variable", ["CI", "GITHUB_ACTIONS"])
@pytest.mark.parametrize("switch, value", [("IKP_TODAY", "2027-03-15"), ("IKP_DATA_DIR", "/tmp")])
def test_switches_are_refused_in_ci(tmp_path, ci_variable, switch, value):
    with pytest.raises(PreviewOverrideError, match=f"{switch} must not be set in CI"):
        _resolve(tmp_path, {switch: value, ci_variable: "true"})


def test_ci_without_switches_is_fine(tmp_path):
    _, settings = _resolve(tmp_path, {"CI": "true", "GITHUB_ACTIONS": "true"})
    assert settings.notice is None
