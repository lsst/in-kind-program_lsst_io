"""Local preview switches for the site build (``IKP_TODAY`` and ``IKP_DATA_DIR``).

Why this file exists
--------------------
Live data can't show every state of the pages: for example, an opportunity
banner that is "upcoming" or "in review" only appears on certain dates. Two
environment variables let a person preview those states on their own machine:

* ``IKP_TODAY=YYYY-MM-DD`` builds the pages as if today were that date;
* ``IKP_DATA_DIR=<folder>`` builds the pages from another ``_data`` folder, such
  as the test fixtures in ``tests/fixtures/``.

These are for **local previews only**. A build that used them would publish
pages that don't match the real data or date, so this module refuses to apply
them when it sees a CI environment (``CI`` or ``GITHUB_ACTIONS`` set), and it
produces a one-line notice that the build prints, so a preview can never be
mistaken for a real build.

The logic lives here, not in ``conf.py``, so it can be unit-tested. It does not
import Sphinx and does not read ``os.environ`` itself: the caller passes the
environment in.
"""

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

# Environment variables that are set when a build runs in CI.
CI_VARIABLES = ("CI", "GITHUB_ACTIONS")

TODAY_VARIABLE = "IKP_TODAY"
DATA_DIR_VARIABLE = "IKP_DATA_DIR"


class PreviewOverrideError(ValueError):
    """A preview switch was used wrongly (bad value, or set in CI)."""


@dataclass(frozen=True)
class PreviewSettings:
    """What the build should use: the data folder and the date to treat as "today"."""

    data_dir: Path
    today: datetime.date
    # One line naming the active overrides, or None when nothing is overridden.
    notice: Optional[str]


def resolve_preview_settings(
    environ: Mapping[str, str],
    default_data_dir: Path,
    real_today: datetime.date,
) -> PreviewSettings:
    """Apply the preview switches found in ``environ`` to the defaults.

    An unset or empty switch means "no override". Raises ``PreviewOverrideError``
    if a switch is set while a CI variable is set, if ``IKP_TODAY`` is not a
    valid ``YYYY-MM-DD`` date, or if ``IKP_DATA_DIR`` is not an existing folder.
    """
    today_text = environ.get(TODAY_VARIABLE, "").strip()
    data_dir_text = environ.get(DATA_DIR_VARIABLE, "").strip()

    if not today_text and not data_dir_text:
        return PreviewSettings(default_data_dir, real_today, notice=None)

    # Refuse before doing anything else: a preview override must never reach a
    # build that CI could publish.
    ci_set = [name for name in CI_VARIABLES if environ.get(name, "").strip()]
    if ci_set:
        active = [
            name for name, text in
            ((TODAY_VARIABLE, today_text), (DATA_DIR_VARIABLE, data_dir_text))
            if text
        ]
        raise PreviewOverrideError(
            f"{' and '.join(active)} must not be set in CI ({ci_set[0]} is set). "
            "These switches are for local preview builds only; unset them."
        )

    today = real_today
    data_dir = default_data_dir
    active_overrides = []

    if today_text:
        try:
            today = datetime.date.fromisoformat(today_text)
        except ValueError:
            raise PreviewOverrideError(
                f"{TODAY_VARIABLE}={today_text!r} is not a valid date; use YYYY-MM-DD, "
                "for example 2027-03-15."
            ) from None
        active_overrides.append(f"{TODAY_VARIABLE}={today.isoformat()}")

    if data_dir_text:
        data_dir = Path(data_dir_text).expanduser().resolve()
        if not data_dir.is_dir():
            raise PreviewOverrideError(
                f"{DATA_DIR_VARIABLE}={data_dir_text!r} is not an existing folder "
                f"(looked for {data_dir})."
            )
        active_overrides.append(f"{DATA_DIR_VARIABLE}={data_dir}")

    notice = "IKP preview override: " + ", ".join(active_overrides)
    return PreviewSettings(data_dir, today, notice)
