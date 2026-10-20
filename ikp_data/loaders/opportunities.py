"""Opportunities banner: turn opportunity YAML records into the page's data.

What the page needs
-------------------
The Telescopes page shows a banner for each open call (an observing
opportunity with a deadline and a list of milestones), taken from
``_data/opportunities/<name>.yaml``.

Why the derived fields exist
----------------------------
* ``slug``: the file name, used as the banner's anchor.
* ``is_visible``: false once ``visible_until`` has passed (the banner is then
  hidden); needs today's date, which the caller passes in.
* ``next_milestone_date``: the soonest milestone that is today or later, so the
  banner can show "next: ..." and so banners sort soonest-first.

The context also needs ``cid_to_slugs`` from the telescopes context so a banner
can link to facility cards; ``ikp_data.loaders.build_contexts`` adds it.
"""

import datetime

import yaml

from ikp_data.derive import normalize_strings


def load_opportunities(data_dir, today):
    """Build the `contributed_opportunities` context from `data_dir`/opportunities.

    `today` decides which opportunities are still visible and which milestones
    are still ahead. `build_contexts` adds `cid_to_slugs` afterwards.
    """
    records_dir = data_dir / "opportunities"
    records = []
    for path in sorted(records_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            record = yaml.safe_load(f) or {}
        record = normalize_strings(record)
        record["slug"] = path.stem

        visible_until = record.get("visible_until")
        if isinstance(visible_until, str):
            visible_until = datetime.date.fromisoformat(visible_until)
        record["is_visible"] = visible_until is None or today <= visible_until

        milestones = record.get("milestones") or []
        upcoming = [
            m for m in milestones
            if isinstance(m.get("date"), (datetime.date, str))
        ]

        def _milestone_date(m):
            d = m.get("date")
            if isinstance(d, str):
                return datetime.date.fromisoformat(d)
            return d

        future_milestones = [m for m in upcoming if _milestone_date(m) >= today]
        record["next_milestone_date"] = (
            min((_milestone_date(m) for m in future_milestones), default=None)
        )
        records.append(record)

    visible_records = [r for r in records if r["is_visible"]]
    visible_records.sort(
        key=lambda r: (r["next_milestone_date"] is None, r["next_milestone_date"])
    )

    return {"opportunities": visible_records}
