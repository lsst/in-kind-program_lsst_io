"""Opportunities banner: turn opportunity YAML records into the page's data.

What the page needs
-------------------
The Telescopes page shows a banner for each opportunity that is still visible
(an observing call with a deadline and a list of milestones), taken from
``_data/opportunities/<name>.yaml``.

Why the derived fields exist
----------------------------
* ``slug``: the file name, used as the banner's anchor.
* ``phase``: where the opportunity is in its lifecycle on today's date
  ("upcoming", "open", "in_review", "closed" or "hidden"), from
  ``opportunity_phase`` (below). A hidden opportunity is left out of the
  context, so the banner appears only while ``today <= visible_until``.
* ``passed`` (on each milestone): true once the milestone's date is before
  today, from ``milestone_passed`` (below); it drives the strike-through.
* ``date_text`` (on each milestone): the date as the banner shows it. A
  ``display_date`` written in the record wins (for example "March 2027");
  otherwise the date is written like "30 Sep 2026".
* ``next_milestone_date``: the soonest milestone that is today or later, so
  banners sort soonest-first.

``opportunity_phase`` and ``milestone_passed`` are pure functions, so they can be
tested without any files. Today's date comes from the caller.

The context also needs ``cid_to_slugs`` from the telescopes context so a banner
can link to facility cards; ``ikp_data.loaders.build_contexts`` adds it.
"""

import yaml

from ikp_data.derive import format_date, normalize_strings, parse_date


def _dated_milestones(milestones):
    """The dates of every milestone that has a readable date (past or future)."""
    dates = (parse_date(m.get("date")) for m in milestones or [] if isinstance(m, dict))
    return [d for d in dates if d is not None]


def milestone_date_text(milestone):
    """The date of one milestone as the banner shows it.

    A `display_date` written in the record wins, because it can say what a
    precise date cannot ("March 2027"). Otherwise the date is formatted like
    "30 Sep 2026". A date that cannot be read is shown as written, so the banner
    never goes blank (``ikp_data.validate`` reports the bad date).
    """
    if milestone.get("display_date"):
        return milestone["display_date"]
    raw_date = milestone.get("date")
    return format_date(raw_date) or ("" if raw_date is None else str(raw_date))


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

        # The phase also decides visibility: "hidden" means `visible_until` is
        # before today, so such a record is dropped below.
        record["phase"] = opportunity_phase(record, today)

        # `passed` is computed from the date, so it can never go stale.
        for milestone in record.get("milestones") or []:
            if isinstance(milestone, dict):
                milestone["passed"] = milestone_passed(milestone, today)
                milestone["date_text"] = milestone_date_text(milestone)

        dated_milestones = _dated_milestones(record.get("milestones"))
        future_dates = [d for d in dated_milestones if d >= today]
        record["next_milestone_date"] = min(future_dates, default=None)
        records.append(record)

    visible_records = [r for r in records if r["phase"] != "hidden"]
    visible_records.sort(
        key=lambda r: (r["next_milestone_date"] is None, r["next_milestone_date"])
    )

    return {"opportunities": visible_records}


# ---------------------------------------------------------------------------
# Card lifecycle (pure functions; the loader above stores their results)
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
# strictly before today, and the loader's visibility rule: a card is shown
# through its `visible_until` day.
#
# A milestone whose banner text is a month-level `display_date` ("March 2027")
# still carries an exact date, so it is marked passed from the day after that
# exact date, not from the first of the month.
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


def _role_dates(record, role):
    """The readable dates of the milestones with this role, in no particular order."""
    dates = []
    for milestone in record.get("milestones") or []:
        if isinstance(milestone, dict) and milestone.get("role") == role:
            date = parse_date(milestone.get("date"))
            if date is not None:
                dates.append(date)
    return dates


def milestone_passed(milestone, today):
    """True once the milestone's date is strictly before `today`.

    A milestone dated today has not passed yet. A milestone with no readable
    date (for example a purely descriptive one) never counts as passed.
    """
    date = parse_date(milestone.get("date"))
    return date is not None and date < today


def opportunity_phase(record, today):
    """The lifecycle phase of one opportunity record on `today`.

    Returns one of "upcoming", "open", "in_review", "closed" or "hidden".
    `record` is the opportunity dictionary (as loaded from YAML, dates as
    strings or date objects). See the comment block above for the rules,
    including the boundary days and incomplete records.
    """
    visible_until = parse_date(record.get("visible_until"))
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
