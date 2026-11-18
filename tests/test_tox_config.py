"""Guard the tox settings that keep the local preview switches out of CI.

``conf.py`` refuses ``IKP_TODAY`` and ``IKP_DATA_DIR`` when ``CI`` or
``GITHUB_ACTIONS`` is set. tox hides environment variables unless they are listed
in ``pass_env``, and an env that sets its own ``pass_env`` replaces the
``[testenv]`` list. So every such list must repeat both names, or the refusal
would silently stop working in that env.
"""

import configparser
from pathlib import Path

TOX_INI = Path(__file__).resolve().parent.parent / "tox.ini"
REQUIRED_NAMES = {"CI", "GITHUB_ACTIONS"}


def test_every_pass_env_includes_the_ci_variables():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(TOX_INI, encoding="utf-8")

    sections_with_pass_env = [
        name for name in parser.sections()
        if name == "testenv" or parser.has_option(name, "pass_env")
    ]
    # [testenv] must define it, and at least one env overrides it (html, linkcheck).
    assert "testenv" in sections_with_pass_env and len(sections_with_pass_env) > 1

    for name in sections_with_pass_env:
        listed = set(parser.get(name, "pass_env", fallback="").split())
        missing = REQUIRED_NAMES - listed
        assert not missing, f"[{name}] pass_env is missing {sorted(missing)}"
