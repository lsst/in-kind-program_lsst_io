"""Decide whether a Sphinx link check passes, from its output.json report.

Why this exists: Sphinx's linkcheck builder exits non-zero for *every* problem,
including a "timeout" (slow or briefly unreachable host), and Sphinx does not
retry timeouts. A timeout says little about whether the link is really dead,
so failing a pull request on one is noise. This script reads the machine-
readable report instead and applies a more useful policy:

* any ``broken`` link         -> fail (exit 1)
* any ``timeout`` link        -> warn only (GitHub Actions annotation), pass
* zero links actually checked -> fail (exit 1). This guards against a
  misconfiguration (for example an ignore pattern that matches every URL)
  that would otherwise make the check "pass" while testing nothing.

Usage (tox runs this after sphinx-build, whose own exit status is ignored):

    python scripts/linkcheck_gate.py [path/to/output.json]

The default path is ``_build/linkcheck/output.json``. The report has one JSON
object per line, with the keys ``filename``, ``lineno``, ``status``, ``uri``
and ``info`` (plus ``code``).
"""

import json
import sys
from collections import Counter
from pathlib import Path

DEFAULT_REPORT = Path("_build/linkcheck/output.json")

# Statuses that mean a link was really requested (as opposed to "ignored",
# "unchecked" or "local"). Used for the "nothing was checked" guard.
CHECKED_STATUSES = ("working", "redirected", "broken", "timeout")


def read_report(path: Path) -> list[dict]:
    """Return the report's records, one dict per JSON line."""
    with path.open(encoding="utf-8") as report:
        return [json.loads(line) for line in report if line.strip()]


def main(path: Path = DEFAULT_REPORT) -> int:
    """Print a summary and return the process exit status (0 pass, 1 fail)."""
    path = Path(path)
    if not path.exists():
        print(f"ERROR: link check report not found: {path}")
        return 1

    records = read_report(path)
    counts = Counter(record["status"] for record in records)

    print("Link check summary:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    failed = False

    # Timeouts: surface them in the GitHub UI but do not fail the build.
    for record in records:
        if record["status"] == "timeout":
            print(
                f"::warning file={record['filename']},line={record['lineno']}"
                f"::Link check timed out (not treated as broken): "
                f"{record['uri']}"
            )

    # Broken links are the one thing that fails the check.
    for record in records:
        if record["status"] == "broken":
            print(
                f"BROKEN: {record['filename']}:{record['lineno']}: "
                f"{record['uri']} ({record.get('info', '')})"
            )
            failed = True

    # Sanity guard: a "pass" that checked nothing is a misconfiguration.
    checked = sum(counts[status] for status in CHECKED_STATUSES)
    if checked == 0:
        print("ERROR: no links were actually checked (all ignored?).")
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT
    sys.exit(main(report_path))
