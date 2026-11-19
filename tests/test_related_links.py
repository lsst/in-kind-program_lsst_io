"""Tests for the "Also see" links on the Datasets and Software cards.

A card's ``related_contribution_ids`` can name a record of the other type (a
dataset's software, a software item's dataset), which links across to the other
page, or a record of its own type, which links to that card on the same page.
The loader works out each link as plain data (``kind``, ``href``, ``anchor``) so
the templates do not have to interpret URLs.

The tests build small data trees in a temporary folder, so they do not depend on
the real card data (no real record relates two items of the same type).
"""

import datetime

import pytest
import yaml

from ikp_data.loaders import build_contexts

TODAY = datetime.date(2027, 3, 15)


def write_record(data_dir, folder, contribution_id, related):
    """Write the smallest valid dataset or software record into `folder`."""
    record = {
        "contribution_id": contribution_id,
        "title": f"Title of {contribution_id}",
        "last_updated": "2027-03-01",
        "form_data": {},
        "curated": {"related_contribution_ids": related},
    }
    folder_path = data_dir / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / f"{contribution_id}.yaml").write_text(yaml.safe_dump(record), encoding="utf-8")


@pytest.fixture
def data_dir(tmp_path):
    """Datasets AAA-S1 (relates to a dataset, a software item, itself and an
    unknown ID), AAA-S2 and CCC-S1 (relates to its own ID, which a software record
    also has); software BBB-S1 (relates to a software item and a dataset), BBB-S2
    and CCC-S1."""
    write_record(tmp_path, "datasets", "TST-AAA-S1", ["TST-AAA-S2", "TST-BBB-S1", "TST-AAA-S1", "NO-SUCH-ID"])
    write_record(tmp_path, "datasets", "TST-AAA-S2", [])
    write_record(tmp_path, "datasets", "TST-CCC-S1", ["TST-CCC-S1"])  # shares its ID with a software record
    write_record(tmp_path, "software", "TST-BBB-S1", ["TST-BBB-S2", "TST-AAA-S1"])
    write_record(tmp_path, "software", "TST-BBB-S2", [])
    write_record(tmp_path, "software", "TST-CCC-S1", [])
    return tmp_path


def related_of(contexts, page, key, contribution_id):
    record = next(r for r in contexts[page][key] if r["contribution_id"] == contribution_id)
    return {rel["contribution_id"]: rel for rel in record["related"]}


def test_dataset_relating_to_a_dataset_links_within_the_page(data_dir):
    contexts = build_contexts(data_dir, today=TODAY)
    rel = related_of(contexts, "contributed_datasets", "datasets", "TST-AAA-S1")["TST-AAA-S2"]
    assert rel["kind"] == "dataset"
    assert rel["anchor"] == "ds-cid-tst-aaa-s2"
    assert rel["href"] == "#ds-cid-tst-aaa-s2"


def test_software_relating_to_software_links_within_the_page(data_dir):
    contexts = build_contexts(data_dir, today=TODAY)
    rel = related_of(contexts, "contributed_software", "software", "TST-BBB-S1")["TST-BBB-S2"]
    assert rel["kind"] == "software"
    assert rel["anchor"] == "sw-cid-tst-bbb-s2"
    assert rel["href"] == "#sw-cid-tst-bbb-s2"


def test_links_to_the_other_type_still_go_to_the_other_page(data_dir):
    contexts = build_contexts(data_dir, today=TODAY)
    dataset_rel = related_of(contexts, "contributed_datasets", "datasets", "TST-AAA-S1")["TST-BBB-S1"]
    assert dataset_rel["kind"] == "software"
    assert dataset_rel["href"] == "contributed-software.html#sw-cid-tst-bbb-s1"
    software_rel = related_of(contexts, "contributed_software", "software", "TST-BBB-S1")["TST-AAA-S1"]
    assert software_rel["kind"] == "dataset"
    assert software_rel["href"] == "contributed-datasets.html#ds-cid-tst-aaa-s1"


def test_an_id_naming_both_a_dataset_and_software_links_to_the_other_page(data_dir):
    """One contribution can deliver both; the dataset's link goes to its software."""
    contexts = build_contexts(data_dir, today=TODAY)
    rel = related_of(contexts, "contributed_datasets", "datasets", "TST-CCC-S1")["TST-CCC-S1"]
    assert rel["kind"] == "software"
    assert rel["href"] == "contributed-software.html#sw-cid-tst-ccc-s1"


def test_a_card_never_links_to_itself(data_dir):
    contexts = build_contexts(data_dir, today=TODAY)
    rel = related_of(contexts, "contributed_datasets", "datasets", "TST-AAA-S1")["TST-AAA-S1"]
    assert rel["href"] is None and rel["kind"] is None


def test_an_unknown_id_has_no_link(data_dir):
    contexts = build_contexts(data_dir, today=TODAY)
    rel = related_of(contexts, "contributed_datasets", "datasets", "TST-AAA-S1")["NO-SUCH-ID"]
    assert rel["href"] is None and rel["anchor"] is None
