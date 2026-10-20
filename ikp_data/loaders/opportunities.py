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

* ``opportunity_phase`` and ``milestone_passed`` (below): pure functions for the
  card lifecycle. They are tested but **not yet used by the loader or the
  template**; a later milestone wires them into the context.

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


# ---------------------------------------------------------------------------
# Card lifecycle (pure functions; not yet part of the context)
# ---------------------------------------------------------------------------
#
# The phases and the rules for incomplete records come from the opportunity
# lifecycle design. A milestone may carry a `role`: "opens", "deadline",
# "results" or "next". From the dated roles and `visible_until`:
#
#   hidden     today is after `visible_until`
#   upcoming   today is before the `opens` date
#   open       from `opens` through the LAST `deadline`
#   in_review  after the last deadline, through the `results` date
#   closed     after `results` (or after the last deadline if there is no
#              `results`), until `visible_until`
#
# Boundary days: every phase lasts THROUGH its end date, inclusive. So the
# deadline day itself is still `open` (the card says "Deadline <date>", and a
# proposal due that day is still welcome), the `results` day is still
# `in_review`, and the `visible_until` day is still shown. This matches
# `milestone_passed`, which treats a milestone as passed only once its date is
# strictly before today, and the loader's `today <= visible_until` visibility.
#
# Incomplete records:
#   * no `opens`: never `upcoming` (open from the start);
#   * no `deadline`: `open` until `visible_until` (then hidden);
#   * several `deadline`s: the last one decides;
#   * several `opens`: the earliest one decides;
#   * several `results`: the latest one decides;
#   * no `results`: `open` goes straight to `closed`;
#   * no `visible_until` (the schema requires it, so this is only defensive):
#     the card is never `hidden`.


def _as_date(value):
    """A date from a date object or an ISO "YYYY-MM-DD" string; None if unreadable."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _role_dates(record, role):
    """The readable dates of the milestones with this role, in no particular order."""
    dates = []
    for milestone in record.get("milestones") or []:
        if isinstance(milestone, dict) and milestone.get("role") == role:
            date = _as_date(milestone.get("date"))
            if date is not None:
                dates.append(date)
    return dates


def milestone_passed(milestone, today):
    """True once the milestone's date is strictly before `today`.

    A milestone dated today has not passed yet. A milestone with no readable
    date (for example a purely descriptive one) never counts as passed.
    """
    date = _as_date(milestone.get("date"))
    return date is not None and date < today


def opportunity_phase(record, today):
    """The lifecycle phase of one opportunity record on `today`.

    Returns one of "upcoming", "open", "in_review", "closed" or "hidden".
    `record` is the opportunity dictionary (as loaded from YAML, dates as
    strings or date objects). See the comment block above for the rules,
    including the boundary days and incomplete records.
    """
    visible_until = _as_date(record.get("visible_until"))
    if visible_until is not None and today > visible_until:
        return "hidden"

    opens = min(_role_dates(record, "opens"), default=None)
    if opens is not None and today < opens:
        return "upcoming"

    last_deadline = max(_role_dates(record, "deadline"), default=None)
    if last_deadline is None or today <= last_deadline:
        return "open"

    results = max(_role_dates(record, "results"), default=None)
    if results is not None and today <= results:
        return "in_review"

    return "closed"
