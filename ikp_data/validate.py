"""Command-line validator for the card data under docs/contribution-types/_data/.

Usage (from the repository root)::

    python -m ikp_data.validate [--data-dir PATH] [--strict]

What it does
------------
1. Loads every ``*.yaml`` file in the data sub-folders (telescopes,
   opportunities, datasets, software, idacs) with ``yaml.safe_load``. It
   validates the raw file contents, never the enriched dictionaries the
   loaders (``ikp_data.loaders``) build, because the models forbid the derived keys.
2. Validates each file against its pydantic model (``ikp_data.schemas``).
3. Runs the cross-record checks (``ikp_data.checks``).
4. Prints a report grouped by file.

Exit status
-----------
* Default (warn-only): always 0 when the data folder could be read, even if
  problems were found, so it can be introduced without blocking anyone.
* ``--strict``: 1 if there is any *error* (warnings alone do not fail).
* 2 if the data folder does not exist.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from pydantic import ValidationError

from ikp_data.checks import Problem, RecordFile, run_all_checks
from ikp_data.schemas import MODEL_FOR_FOLDER

# docs/contribution-types/_data, found relative to the repository root
# (the folder that contains this package).
DEFAULT_DATA_DIR = (
    Path(__file__).resolve().parent.parent / "docs" / "contribution-types" / "_data"
)


def _format_location(location: tuple) -> str:
    """Turn a pydantic error location like ('form_data', 'email') into 'form_data.email'."""
    return ".".join(str(part) for part in location) or "(whole record)"


def validate_data_dir(data_dir: Path) -> tuple[list[Problem], int]:
    """Validate every record under ``data_dir``.

    Returns the list of problems and the number of files checked.
    """
    problems: list[Problem] = []
    loaded: list[RecordFile] = []
    file_count = 0

    for folder_name, model in MODEL_FOR_FOLDER.items():
        folder = data_dir / folder_name
        if not folder.is_dir():
            problems.append(
                Problem("error", f"{folder_name}/", "expected data folder is missing")
            )
            continue
        for path in sorted(folder.glob("*.yaml")):
            file_count += 1
            label = f"{folder_name}/{path.name}"
            try:
                with path.open(encoding="utf-8") as handle:
                    data = yaml.safe_load(handle)
            except yaml.YAMLError as err:
                problems.append(Problem("error", label, f"not valid YAML: {err}"))
                continue
            loaded.append(RecordFile(folder_name, label, data))

            try:
                model.model_validate(data)
            except ValidationError as err:
                for item in err.errors():
                    problems.append(
                        Problem(
                            "error",
                            label,
                            f"{_format_location(item['loc'])}: {item['msg']}",
                        )
                    )

    problems.extend(run_all_checks(loaded))
    return problems, file_count


def format_report(problems: list[Problem], file_count: int) -> str:
    """Build the human-readable report, grouped by file."""
    by_file: dict[str, list[Problem]] = defaultdict(list)
    for problem in problems:
        by_file[problem.file].append(problem)

    lines: list[str] = []
    for file in sorted(by_file):
        lines.append(file)
        for problem in by_file[file]:
            lines.append(f"  {problem.severity.upper():7} {problem.message}")
        lines.append("")

    errors = sum(1 for p in problems if p.severity == "error")
    warnings = sum(1 for p in problems if p.severity == "warning")
    lines.append(
        f"Checked {file_count} files: {errors} error(s), {warnings} warning(s) "
        f"in {len(by_file)} file(s)."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: validate the card data and return the exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m ikp_data.validate",
        description="Validate the Rubin In-Kind Program card data files.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Folder holding telescopes/, opportunities/, datasets/, software/ and idacs/ "
        f"(default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if any error is found (default: report only).",
    )
    args = parser.parse_args(argv)

    if not args.data_dir.is_dir():
        print(f"Data folder not found: {args.data_dir}", file=sys.stderr)
        return 2

    problems, file_count = validate_data_dir(args.data_dir)
    print(format_report(problems, file_count))

    has_errors = any(p.severity == "error" for p in problems)
    return 1 if (args.strict and has_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
