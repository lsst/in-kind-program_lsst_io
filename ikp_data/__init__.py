"""The Rubin In-Kind Program site's data model.

This package describes what a valid card record looks like, independent of how
the site renders it:

* ``ikp_data.schemas``  - one pydantic model per record type (telescope,
  opportunity, dataset, software, IDAC).
* ``ikp_data.checks``   - checks that need more than one record (unique IDs,
  cross-references, sibling consistency, milestone ordering).
* ``ikp_data.validate`` - a command-line validator that runs both over the
  YAML files in ``docs/contribution-types/_data/``.

Run the validator from the repository root with::

    python -m ikp_data.validate [--data-dir PATH] [--strict]
"""
