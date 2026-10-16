"""Pytest configuration for the conf.py golden-snapshot tests.

Adds the `--update-snapshots` command-line option. Without it the tests only
*compare* against the committed golden files; with it they rewrite those files.
Rewriting is for an intended, reviewed change only (see tests/README.md).
"""


def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Rewrite tests/snapshots/*.json from the current loader output.",
    )
