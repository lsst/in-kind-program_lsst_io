"""Loaders: turn the card YAML files into the data each page template renders.

Why this package exists
-----------------------
Sphinx renders the Contributed pages from Jinja templates (via the
``sphinx_jinja`` extension), and each template needs a "context": a dictionary
of cleaned-up records plus derived fields such as slugs, filter tokens and map
positions. This package builds those contexts. It used to live inside the
site's ``conf.py``; keeping it here makes it importable and testable on its own.

There is one module per record type (``datasets``, ``telescopes``,
``opportunities``, ``software``, ``idacs``) and ``build_contexts`` below calls
them all. Shared helpers are in ``ikp_data.derive``.

Nothing here reads the clock or finds files relative to its own location:
the caller passes the data folder and today's date.
"""

import datetime
from pathlib import Path

from ikp_data.loaders.datasets import load_datasets
from ikp_data.loaders.idacs import load_idacs
from ikp_data.loaders.opportunities import load_opportunities
from ikp_data.loaders.software import load_software
from ikp_data.loaders.telescopes import load_telescopes


def build_contexts(data_dir: Path, today: datetime.date) -> dict:
    """Build every page's Jinja context.

    Parameters
    ----------
    data_dir:
        The ``_data`` folder (``docs/contribution-types/_data``), containing one
        sub-folder of YAML files per record type.
    today:
        The date to treat as "now" (which opportunities are visible).

    Returns a dict keyed by the context names the ``.rst`` templates use:
    ``contributed_datasets``, ``contributed_telescopes``,
    ``contributed_opportunities``, ``contributed_software`` and
    ``contributed_idacs``.
    """
    # The map pages inline the outline from docs/_static/world-outline.svg. It
    # is not under `data_dir`, so we derive it here, in one place, from the
    # fixed site layout: data_dir is docs/contribution-types/_data, so the docs
    # folder is two levels up.
    docs_dir = data_dir.parent.parent
    world_outline_svg = docs_dir / "_static" / "world-outline.svg"

    # The telescopes context is built first because the opportunities banner
    # links to facility cards by contribution ID, and the per-card anchors
    # (slugs) are computed there.
    telescopes = load_telescopes(data_dir, world_outline_svg)
    opportunities = load_opportunities(data_dir, today)
    opportunities["cid_to_slugs"] = telescopes["cid_to_slugs"]

    # Datasets and software look up each other's titles straight from the
    # YAML files, so their order does not matter.
    return {
        "contributed_datasets": load_datasets(data_dir, today),
        "contributed_telescopes": telescopes,
        "contributed_opportunities": opportunities,
        "contributed_software": load_software(data_dir, today),
        "contributed_idacs": load_idacs(data_dir, world_outline_svg),
    }
