"""Tests for scripts/linkcheck_gate.py using small synthetic reports.

Each test writes a tiny output.json (one JSON object per line, as Sphinx does)
into a temporary directory and checks the gate's exit status and output.
"""

import json
import sys
from pathlib import Path

# scripts/ is not a package, so make it importable for this test only.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import linkcheck_gate  # noqa: E402


def write_report(tmp_path, statuses):
    """Write a report with one record per status; return its path."""
    report = tmp_path / "output.json"
    lines = [
        json.dumps(
            {
                "filename": "contributed/example.rst",
                "lineno": number,
                "status": status,
                "code": 0,
                "uri": f"https://example.org/{number}",
                "info": "",
            }
        )
        for number, status in enumerate(statuses, start=1)
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def test_all_working_passes(tmp_path):
    report = write_report(tmp_path, ["working", "redirected", "ignored"])
    assert linkcheck_gate.main(report) == 0


def test_timeout_warns_but_passes(tmp_path, capsys):
    report = write_report(tmp_path, ["working", "timeout"])
    assert linkcheck_gate.main(report) == 0
    assert "::warning file=contributed/example.rst,line=2::" in (
        capsys.readouterr().out
    )


def test_broken_fails(tmp_path, capsys):
    report = write_report(tmp_path, ["working", "broken"])
    assert linkcheck_gate.main(report) == 1
    assert "BROKEN" in capsys.readouterr().out


def test_nothing_checked_fails(tmp_path):
    report = write_report(tmp_path, ["ignored", "ignored"])
    assert linkcheck_gate.main(report) == 1


def test_missing_report_fails(tmp_path):
    assert linkcheck_gate.main(tmp_path / "absent.json") == 1
