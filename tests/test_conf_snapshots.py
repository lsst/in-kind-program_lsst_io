"""Golden-snapshot tests for the data loaders in the site's conf.py.

WHY THIS EXISTS
    The planned move of the loaders out of conf.py into a package is
    meant to change nothing observable. These tests prove that: each Jinja
    context that conf.py builds (the data every card template renders) is
    serialized to stable JSON and compared with a committed "golden" copy. If
    a refactor changes any value, any ordering, or any key, a test fails.

HOW IT WORKS
    * conf.py runs every loader at import time and fills `jinja_contexts`, so
      we simply import it (by path; it is not on sys.path as a package).
      It star-imports `documenteer.conf.guide`, so these tests must run where
      documenteer is installed: `tox run -e test`.
    * The date is frozen while conf.py is imported (see FROZEN_NOW below), so
      the output does not depend on the day the tests run.
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

# conf.py calls datetime.date.today() in two places: the opportunity loader
# (which opportunities are visible, which milestones are in the future) and
# the last-updated fallback. Freezing it keeps the snapshot stable.
#
# 2026-09-15 is chosen because, with the current data, it is the state that
# exercises the opportunity logic best: both opportunities are visible
# (GTC visible until 2026-10-01, NOIRLab CFP until 2026-10-15), and some of
# their milestones are already past while others are still ahead, so the
# "next_milestone_date" logic has real work to do. Today's real date (after
# both banners expire) would give an empty list and test almost nothing.
#
# time-machine is used rather than freezegun: it is faster, patches at the
# C level so `datetime.date.today()` is covered without import-order tricks,
# and is a small, well-maintained, test-only dependency.
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
        return f"<callable {getattr(value, '__name__', 'unknown')}>"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"No stable JSON conversion for {type(value).__name__}: {value!r}")


def dump(value):
    """The exact text stored in (and compared with) a golden file."""
    return json.dumps(to_stable_json(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


@pytest.fixture(scope="session")
def jinja_contexts():
    """Import the site's conf.py with the date frozen; return its jinja_contexts."""
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
    return module.jinja_contexts


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

    conf.py falls back to `git log` when a record has no explicit
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
