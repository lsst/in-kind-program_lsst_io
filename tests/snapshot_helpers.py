"""Helpers shared by the golden-snapshot tests.

``dump`` turns any loader output into the exact text stored in (and compared
with) a golden file, and ``SNAPSHOT_DIR`` is where those files live. Both
``test_conf_snapshots.py`` and ``test_opportunity_loader.py`` use them, so the
two kinds of golden file are written identically.

To update the golden files (intended, reviewed changes only):
    tox run -e test -- --update-snapshots
"""

import datetime
import json
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


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
        # Safety net only: test_contexts_are_plain_data forbids callables in
        # a context. If one slips in, record just that a callable was present
        # (its identity is not data) rather than failing in the snapshot code.
        name = getattr(value, "__name__", "unknown")
        return f"<callable {name}>"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"No stable JSON conversion for {type(value).__name__}: {value!r}")


def dump(value):
    """The exact text stored in (and compared with) a golden file."""
    return json.dumps(to_stable_json(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
