"""Golden-snapshot tests for the card loaders in ikp_data.loaders.

WHY THIS EXISTS
    The loaders turn the card YAML files into the Jinja contexts that every
    card template renders. Each context is serialized to stable JSON and
    compared with a committed "golden" copy, so a refactor that changes any
    value, any ordering, or any key makes a test fail.

HOW IT WORKS
    * The main tests call `build_contexts(data_dir, today=...)` directly. The
      date is a parameter, so no clock freezing is needed (see TODAY below).
    * One extra test imports the site's conf.py with the clock frozen and checks
      its `jinja_contexts` equal the package output. That proves conf.py is wired
      to the package correctly. conf.py star-imports `documenteer.conf.guide`,
      so run these tests where documenteer is installed: `tox run -e test`.
    * Output is made deterministic by `to_stable_json` (sorted keys, dates as
      ISO strings, callables as placeholders, sets as sorted lists).

TO UPDATE THE GOLDEN FILES (intended, reviewed changes only):
    tox run -e test -- --update-snapshots
"""

import datetime
import importlib.util
import json
import os
from pathlib import Path

import pytest
import time_machine
import yaml

from ikp_data.loaders import build_contexts

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
DATA_DIR = REPO_ROOT / "docs" / "contribution-types" / "_data"

# The contexts conf.py defines, one golden file each.
CONTEXT_NAMES = [
    "contributed_datasets",
    "contributed_telescopes",
    "contributed_opportunities",
    "contributed_software",
    "contributed_idacs",
]

# The date passed to the loaders. It decides which opportunities are visible
# and which of their milestones are still ahead.
#
# 2026-09-15 is chosen because, with the current data, it is the state that
# exercises the opportunity logic best: both opportunities are visible
# (GTC visible until 2026-10-01, NOIRLab CFP until 2026-10-15), and some of
# their milestones are already past while others are still ahead, so the
# "next_milestone_date" logic has real work to do. Today's real date (after
# both banners expire) would give an empty list and test almost nothing.
TODAY = datetime.date(2026, 9, 15)

# The same moment as a frozen clock, used only by the test that imports conf.py
# (which calls datetime.date.today() itself). time-machine is used rather than
# freezegun: it is faster, patches at the C level so `datetime.date.today()` is
# covered without import-order tricks, and is a small, test-only dependency.
FROZEN_NOW = datetime.datetime(2026, 9, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


def to_stable_json(value):
    """Convert any loader output to a JSON-serializable, deterministic form."""
    if isinstance(value, dict):
        # Keys are stringified so non-string keys (rare) don't break sorting.
        return {str(k): to_stable_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_stable_json(v) for v in value]
    if isinstance(value, (set, frozenset)):
        # Sets have no defined order; sort by the JSON form of each element.
        return sorted(
            (to_stable_json(v) for v in value),
            key=lambda v: json.dumps(v, sort_keys=True),
        )
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if callable(value):
        # e.g. the `slugify` helper passed to templates. Its identity is not
        # data; record only that a callable was present.
        #
        # The golden files were recorded when this helper was the private
        # `_slugify` in conf.py; it is now the public `slugify` in
        # ikp_data.derive. Spelling the placeholder with a leading underscore
        # keeps the golden files byte-identical across that rename.
        name = getattr(value, "__name__", "unknown").lstrip("_")
        return f"<callable _{name}>"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"No stable JSON conversion for {type(value).__name__}: {value!r}")


def dump(value):
    """The exact text stored in (and compared with) a golden file."""
    return json.dumps(to_stable_json(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


@pytest.fixture(scope="session")
def jinja_contexts():
    """The five contexts, built directly by the package for a fixed date."""
    return build_contexts(DATA_DIR, today=TODAY)


def test_conf_py_wires_the_package(jinja_contexts):
    """conf.py's `jinja_contexts` must equal what the package builds.

    The golden-file tests below skip conf.py entirely, so this one test imports
    it (with the clock frozen) to prove conf.py passes the right data folder and
    uses the package's output unchanged.
    """
    conf_path = REPO_ROOT / "conf.py"
    spec = importlib.util.spec_from_file_location("site_conf", conf_path)
    module = importlib.util.module_from_spec(spec)
    # documenteer reads documenteer.toml from the working directory, so run the
    # import from the repo root regardless of where pytest was launched.
    previous_cwd = Path.cwd()
    try:
        os.chdir(REPO_ROOT)
        with time_machine.travel(FROZEN_NOW, tick=False):
            spec.loader.exec_module(module)
    finally:
        os.chdir(previous_cwd)
    assert dump(module.jinja_contexts) == dump(jinja_contexts)


@pytest.mark.parametrize("name", CONTEXT_NAMES)
def test_context_matches_golden_snapshot(name, jinja_contexts, request):
    actual = dump(jinja_contexts[name])
    golden_path = SNAPSHOT_DIR / f"{name}.json"

    if request.config.getoption("--update-snapshots"):
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        golden_path.write_text(actual, encoding="utf-8")
        return

    assert golden_path.exists(), (
        f"{golden_path} is missing. If this is intended, create it with "
        "`tox run -e test -- --update-snapshots`."
    )
    expected = golden_path.read_text(encoding="utf-8")
    # Comparing whole strings gives pytest's readable line diff on failure.
    assert actual == expected, (
        f"The {name} context differs from {golden_path.name}. If the change is "
        "intended and reviewed, rerun with --update-snapshots (tests/README.md)."
    )


@pytest.mark.parametrize(
    ("context_name", "records_key", "data_subdir"),
    [
        ("contributed_datasets", "datasets", "datasets"),
        ("contributed_software", "software", "software"),
    ],
)
def test_last_updated_comes_from_yaml_not_git(
    context_name, records_key, data_subdir, jinja_contexts
):
    """Every record's last_updated must equal its YAML value.

    The loader falls back to `git log` when a record has no explicit
    last_updated. That would make the snapshot depend on git history, so we
    require the explicit value (ADR 0007) and check it is what the loader used.
    """
    yaml_values = {}
    missing = []
    for path in sorted((DATA_DIR / data_subdir).glob("*.yaml")):
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not record.get("last_updated"):
            missing.append(path.name)
        else:
            yaml_values[record["contribution_id"]] = str(record["last_updated"])

    assert not missing, (
        f"These {data_subdir} records have no explicit last_updated, so the "
        f"snapshot would depend on git history: {missing}"
    )

    records = jinja_contexts[context_name][records_key]
    assert len(records) == len(yaml_values)
    for record in records:
        cid = record["contribution_id"]
        assert record["last_updated"] == yaml_values[cid], cid
