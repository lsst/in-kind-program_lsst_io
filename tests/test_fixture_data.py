"""Tests for the invented fixture data tree in tests/fixtures/.

The fixtures give the loaders a small, stable data set that covers every card
type and every opportunity phase, independent of the real card data. These
tests check that the fixtures themselves stay valid and keep covering what they
promise (see tests/fixtures/README.md).
"""

import datetime
from pathlib import Path

import yaml

from ikp_data import validate
from ikp_data.loaders import build_contexts
from ikp_data.loaders.opportunities import opportunity_phase

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_DATA_DIR = FIXTURES / "docs" / "contribution-types" / "_data"

# The date the fixtures are designed around (see tests/fixtures/README.md).
FIXTURE_TODAY = datetime.date(2027, 3, 15)

# What each fixture opportunity should be on FIXTURE_TODAY.
EXPECTED_PHASES = {
    "fixture-upcoming-call": "upcoming",
    "fixture-open-call": "open",
    "fixture-in-review-call": "in_review",
    "fixture-closed-call": "closed",
    "fixture-hidden-call": "hidden",
}


def test_fixture_tree_passes_strict_validation():
    problems, file_count = validate.validate_data_dir(FIXTURE_DATA_DIR)
    assert problems == []
    assert file_count == 9  # 1 telescope, 1 dataset, 1 software, 1 IDAC, 5 opportunities


def test_fixtures_cover_every_card_type():
    for folder in ("telescopes", "datasets", "software", "idacs", "opportunities"):
        assert list(
            (FIXTURE_DATA_DIR / folder).glob("*.yaml")
        ), f"no fixture record in {folder}/"


def test_build_contexts_works_on_the_fixture_tree():
    contexts = build_contexts(FIXTURE_DATA_DIR, today=FIXTURE_TODAY)
    assert len(contexts["contributed_telescopes"]["telescopes"]) == 1
    assert len(contexts["contributed_datasets"]["datasets"]) == 1
    assert len(contexts["contributed_software"]["software"]) == 1
    assert len(contexts["contributed_idacs"]["idacs"]) == 1
    # The stub outline in tests/fixtures/docs/_static is found by the loaders.
    assert contexts["contributed_telescopes"]["world_outline_path"].startswith("M100")


def test_each_opportunity_phase_is_produced_on_the_fixed_date():
    raw = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (FIXTURE_DATA_DIR / "opportunities").glob("*.yaml")
    }
    assert {name: opportunity_phase(r, FIXTURE_TODAY) for name, r in raw.items()} == EXPECTED_PHASES


def test_loader_hides_only_the_hidden_opportunity():
    contexts = build_contexts(FIXTURE_DATA_DIR, today=FIXTURE_TODAY)
    shown = {r["slug"] for r in contexts["contributed_opportunities"]["opportunities"]}
    assert shown == set(EXPECTED_PHASES) - {"fixture-hidden-call"}


def test_one_dataset_is_highlighted_through_the_fixed_date():
    (record,) = build_contexts(FIXTURE_DATA_DIR, today=FIXTURE_TODAY)["contributed_datasets"]["datasets"]
    highlight = record["curated"]["highlight"]
    assert highlight["reason"]
    assert datetime.date.fromisoformat(highlight["until"]) >= FIXTURE_TODAY


def test_the_software_record_is_highlighted_past_the_dataset_highlight():
    contexts = build_contexts(FIXTURE_DATA_DIR, today=FIXTURE_TODAY)
    (dataset,) = contexts["contributed_datasets"]["datasets"]
    (software,) = contexts["contributed_software"]["software"]
    software_highlight = software["curated"]["highlight"]
    assert software_highlight["reason"]
    # The two end dates differ, so a date can fall between them and show one row only.
    assert software_highlight["until"] > dataset["curated"]["highlight"]["until"]
