"""Tests for ikp_data: schemas, cross-record checks and the validator CLI.

Two kinds of test live here:

1. Every real record under docs/contribution-types/_data/ must validate, except
   a short, explicit list of known failures (see KNOWN_FAILURES).
2. Deliberately broken records must be rejected. These use in-memory copies of a
   real record that are then damaged, so no data file is touched.
"""

import copy
import datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ikp_data import checks, schemas, validate

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "contribution-types" / "_data"

# Real files that are expected to fail validation, with the reason. Empty now that
# all card data is clean; the mechanism stays so a future known failure can be listed
# explicitly (the test below fails if a listed file starts to pass).
KNOWN_FAILURES: dict[str, str] = {}


def _all_record_paths():
    paths = []
    for folder in schemas.MODEL_FOR_FOLDER:
        paths.extend(sorted((DATA_DIR / folder).glob("*.yaml")))
    return paths


def _load(relative_path):
    with (DATA_DIR / relative_path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _model_for(relative_path):
    return schemas.MODEL_FOR_FOLDER[relative_path.split("/")[0]]


def _error_locations(model, data):
    """Validate and return the set of top-level error locations (empty if valid)."""
    try:
        model.model_validate(data)
    except ValidationError as err:
        return {e["loc"][0] for e in err.errors()}, err
    return set(), None


# ---------------------------------------------------------------------------
# Real data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", _all_record_paths(), ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_real_record_validates_or_is_a_known_failure(path):
    relative = f"{path.parent.name}/{path.name}"
    model = _model_for(relative)
    locations, _ = _error_locations(model, _load(relative))
    if relative in KNOWN_FAILURES:
        assert locations == {KNOWN_FAILURES[relative]}, (
            f"{relative} should fail only on '{KNOWN_FAILURES[relative]}'; "
            "if it now passes, remove it from KNOWN_FAILURES"
        )
    else:
        assert locations == set()


def test_every_field_has_description_and_rendered_flag():
    """Each field must carry help text and a boolean 'rendered' flag (checked recursively)."""
    seen_models = set()

    def check_model(model):
        if model in seen_models:
            return
        seen_models.add(model)
        for name, info in model.model_fields.items():
            where = f"{model.__name__}.{name}"
            assert info.description, f"{where} has no description"
            extra = info.json_schema_extra
            assert isinstance(extra, dict) and isinstance(extra.get("rendered"), bool), (
                f"{where} has no boolean 'rendered' flag"
            )
            for nested in _nested_models(info.annotation):
                check_model(nested)

    for model in schemas.MODEL_FOR_FOLDER.values():
        check_model(model)
    assert len(seen_models) > len(schemas.MODEL_FOR_FOLDER)  # nested models were visited


def test_highlight_fields_are_rendered_but_not_content_updates():
    """Highlights show on the page but must not bump last_updated; other fields default to rendered."""
    highlight_fields = [
        schemas.Highlight.model_fields["reason"],
        schemas.Highlight.model_fields["until"],
        schemas.DatasetCurated.model_fields["highlight"],
        schemas.SoftwareCurated.model_fields["highlight"],
    ]
    for info in highlight_fields:
        assert info.json_schema_extra["rendered"] is True
        assert schemas.counts_as_content_update(info) is False
    assert schemas.counts_as_content_update(schemas.Telescope.model_fields["summary"]) is True
    # A field that is not rendered is not a content update either.
    assert schemas.counts_as_content_update(schemas.DatasetCurated.model_fields["needs_review"]) is False


def _nested_models(annotation):
    """Yield BaseModel subclasses mentioned anywhere inside a type annotation."""
    from typing import get_args

    if isinstance(annotation, type) and issubclass(annotation, schemas.BaseModel):
        yield annotation
    for arg in get_args(annotation):
        yield from _nested_models(arg)


# ---------------------------------------------------------------------------
# Deliberately broken records
# ---------------------------------------------------------------------------

DATASET_FILE = "datasets/" + sorted(p.name for p in (DATA_DIR / "datasets").glob("*.yaml"))[0]
SOFTWARE_FILE = "software/" + sorted(p.name for p in (DATA_DIR / "software").glob("*.yaml"))[0]
TELESCOPE_FILE = "telescopes/JAP-JPG-S1-subaru.yaml"


def _dataset():
    return copy.deepcopy(_load(DATASET_FILE))


def _software():
    return copy.deepcopy(_load(SOFTWARE_FILE))


def _telescope():
    return copy.deepcopy(_load(TELESCOPE_FILE))


def _opportunity():
    """A valid opportunity: a deep copy of the real NOIRLab record."""
    return copy.deepcopy(_load("opportunities/noirlab-cfp-2027a.yaml"))


def test_clean_copies_of_real_records_validate():
    """Guards the other tests: damage below is the only reason they fail."""
    schemas.Dataset.model_validate(_dataset())
    schemas.Software.model_validate(_software())
    schemas.Telescope.model_validate(_telescope())
    schemas.Opportunity.model_validate(_opportunity())


@pytest.mark.parametrize("pii_key", ["email", "submitter_name", "name"])
def test_dataset_rejects_submitter_pii_in_form_data(pii_key):
    record = _dataset()
    record["form_data"][pii_key] = "someone@example.org"
    with pytest.raises(ValidationError) as excinfo:
        schemas.Dataset.model_validate(record)
    assert f"form_data.{pii_key}" in str(excinfo.value)
    assert "personal information" in str(excinfo.value)


def test_software_rejects_submitter_name():
    record = _software()
    record["form_data"]["submitter_name"] = "Some Person"
    with pytest.raises(ValidationError) as excinfo:
        schemas.Software.model_validate(record)
    assert "form_data.submitter_name" in str(excinfo.value)


def test_associated_dataset_rejects_pii_too():
    record = _software()
    record["form_data"]["associated_dataset"] = {"submitted": True, "email": "a@b.org"}
    with pytest.raises(ValidationError):
        schemas.Software.model_validate(record)


def test_dataset_missing_last_updated_fails():
    record = _dataset()
    del record["last_updated"]
    with pytest.raises(ValidationError) as excinfo:
        schemas.Dataset.model_validate(record)
    assert "last_updated" in str(excinfo.value)


@pytest.mark.parametrize(
    "bad_value",
    [
        "2026-7-22",  # month not zero-padded
        "2026-02-30",  # not a real date
        "22/07/2026",  # wrong format
        "",  # empty
    ],
)
def test_last_updated_wrong_format_fails(bad_value):
    for make, model in ((_dataset, schemas.Dataset), (_software, schemas.Software)):
        record = make()
        record["last_updated"] = bad_value
        with pytest.raises(ValidationError):
            model.model_validate(record)


def test_unquoted_last_updated_fails_with_helpful_message():
    """YAML turns an unquoted date into a date object; the schema asks for quotes."""
    record = yaml.safe_load(
        yaml.safe_dump(_dataset()).replace(
            f"last_updated: '{_dataset()['last_updated']}'", "last_updated: 2026-07-22"
        )
    )
    assert isinstance(record["last_updated"], datetime.date)
    with pytest.raises(ValidationError) as excinfo:
        schemas.Dataset.model_validate(record)
    assert "quote it" in str(excinfo.value)


def test_telescope_unknown_status_fails():
    record = _telescope()
    record["status"] = "coming_soon"
    with pytest.raises(ValidationError) as excinfo:
        schemas.Telescope.model_validate(record)
    assert "status" in str(excinfo.value)


@pytest.mark.parametrize("missing", ["latitude", "longitude"])
def test_telescope_missing_coordinate_fails(missing):
    record = _telescope()
    del record[missing]
    with pytest.raises(ValidationError) as excinfo:
        schemas.Telescope.model_validate(record)
    assert missing in str(excinfo.value)


def test_unknown_top_level_key_fails():
    for record, model in (
        (_dataset(), schemas.Dataset),
        (_software(), schemas.Software),
        (_telescope(), schemas.Telescope),
        (_opportunity(), schemas.Opportunity),
    ):
        record["surprise_key"] = 1
        with pytest.raises(ValidationError) as excinfo:
            model.model_validate(record)
        assert "surprise_key" in str(excinfo.value)


def test_status_override_must_be_a_known_value():
    record = _dataset()
    record["curated"]["status_override"] = "delivered"  # a software value, not a dataset one
    with pytest.raises(ValidationError):
        schemas.Dataset.model_validate(record)
    record["curated"]["status_override"] = "not_yet_delivered"
    schemas.Dataset.model_validate(record)


def test_highlight_shape():
    record = _dataset()
    record["curated"]["highlight"] = {"reason": "Newly delivered", "until": "2026-12-01"}
    schemas.Dataset.model_validate(record)
    record["curated"]["highlight"]["until"] = "soon"
    with pytest.raises(ValidationError):
        schemas.Dataset.model_validate(record)


def test_opportunity_requires_visible_until_and_known_accent_and_role():
    record = _opportunity()
    del record["visible_until"]
    with pytest.raises(ValidationError):
        schemas.Opportunity.model_validate(record)

    record = _opportunity()
    record["accent"] = "danger"
    with pytest.raises(ValidationError):
        schemas.Opportunity.model_validate(record)

    record = _opportunity()
    record["milestones"][0]["role"] = "finale"
    with pytest.raises(ValidationError):
        schemas.Opportunity.model_validate(record)


def test_opportunity_contact_block_is_not_declared():
    record = _opportunity()
    record["contact"] = None
    with pytest.raises(ValidationError):
        schemas.Opportunity.model_validate(record)


def test_deprecated_passed_flag_is_still_accepted():
    record = _opportunity()
    record["milestones"][0]["passed"] = True
    schemas.Opportunity.model_validate(record)


# ---------------------------------------------------------------------------
# Cross-record checks
# ---------------------------------------------------------------------------


def _milestones(*roles_and_dates):
    return {
        "milestones": [
            {"label": f"{role or 'info'} {date}", "date": date, **({"role": role} if role else {})}
            for role, date in roles_and_dates
        ]
    }


def test_results_before_last_deadline_is_an_error():
    problems = checks.check_milestone_order(
        "opportunities/x.yaml",
        _milestones(("deadline", "2026-10-01"), ("deadline", "2026-11-01"), ("results", "2026-10-15")),
    )
    assert [p.severity for p in problems] == ["error"]
    assert "must be after the last deadline" in problems[0].message


def test_next_must_follow_results_or_last_deadline():
    # With a results milestone, next is compared with results.
    problems = checks.check_milestone_order(
        "x",
        _milestones(("deadline", "2026-10-01"), ("results", "2026-12-01"), ("next", "2026-11-01")),
    )
    assert len(problems) == 1 and "results" in problems[0].message
    # Without results, next is compared with the last deadline.
    problems = checks.check_milestone_order(
        "x", _milestones(("deadline", "2026-10-01"), ("next", "2026-09-01"))
    )
    assert len(problems) == 1 and "last deadline" in problems[0].message


def test_well_ordered_milestones_pass():
    assert not checks.check_milestone_order(
        "x",
        _milestones(
            ("opens", "2026-08-01"),
            ("deadline", "2026-09-01"),
            (None, "2026-09-15"),
            ("results", "2026-10-01"),
            ("next", "2027-03-01"),
        ),
    )


def _record(record_type, file, **data):
    return checks.RecordFile(record_type, file, data)


def test_duplicate_dataset_contribution_id_is_an_error():
    problems = checks.check_unique_ids(
        [
            _record("datasets", "datasets/a.yaml", contribution_id="X-1"),
            _record("datasets", "datasets/b.yaml", contribution_id="X-1"),
        ]
    )
    assert [p.severity for p in problems] == ["error"]


def test_telescope_siblings_may_share_a_contribution_id():
    problems = checks.check_unique_ids(
        [
            _record("telescopes", "telescopes/X-1-a.yaml", contribution_id="X-1"),
            _record("telescopes", "telescopes/X-1-b.yaml", contribution_id="X-1"),
        ]
    )
    assert problems == []


def test_unresolved_related_id_is_an_error():
    records = [
        _record("datasets", "datasets/a.yaml", contribution_id="D-1"),
        _record(
            "software",
            "software/b.yaml",
            contribution_id="S-1",
            curated={"related_contribution_ids": ["D-1", "NOPE-9"]},
        ),
    ]
    problems = checks.check_related_ids_resolve(records)
    assert len(problems) == 1 and "NOPE-9" in problems[0].message


def test_sibling_disagreement_is_a_warning_but_different_facilities_are_skipped():
    same_facility = [
        _record("telescopes", "telescopes/a.yaml", contribution_id="K-1", facility="KMT", summary="one"),
        _record("telescopes", "telescopes/b.yaml", contribution_id="K-1", facility="KMT", summary="two"),
    ]
    problems = checks.check_telescope_siblings(same_facility)
    assert [p.severity for p in problems] == ["warning"]

    different = [
        _record("telescopes", "telescopes/a.yaml", contribution_id="V-1", facility="VST", summary="one"),
        _record("telescopes", "telescopes/b.yaml", contribution_id="V-1", facility="LBT", summary="two"),
    ]
    assert checks.check_telescope_siblings(different) == []


# ---------------------------------------------------------------------------
# Validator command line
# ---------------------------------------------------------------------------


def test_validator_exit_codes_on_real_data(capsys):
    """Warn-only exits 0 even with errors; --strict exits 1 while the data has errors."""
    assert validate.main([]) == 0
    problems, file_count = validate.validate_data_dir(DATA_DIR)
    assert file_count == len(_all_record_paths())
    errors = [p for p in problems if p.severity == "error"]
    assert {p.file for p in errors} <= set(KNOWN_FAILURES)
    assert validate.main(["--strict"]) == (1 if errors else 0)
    assert f"Checked {len(_all_record_paths())} files" in capsys.readouterr().out


def test_validator_missing_data_dir_exits_2(tmp_path):
    assert validate.main(["--data-dir", str(tmp_path / "nope")]) == 2
