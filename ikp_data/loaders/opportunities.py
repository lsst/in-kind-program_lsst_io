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
* ``status_line``: one short sentence for the top of the banner that says what
  the phase means for the reader, for example "Deadline 30 Sep 2026" (see
  ``phase_status_line``). Empty when the record lacks the milestone the phase
  needs, in which case the banner shows no status line.
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

        record["status_line"] = phase_status_line(record)

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


# ---------------------------------------------------------------------------
# The status line at the top of a banner
# ---------------------------------------------------------------------------


def _milestone_with_role(record, role, pick, skip_passed=False):
    """The milestone with this role whose date `pick` chooses (`min` or `max`).

    Milestones without a readable date are ignored. With `skip_passed`, so are
    milestones the loader has marked `passed`. Returns None if no milestone is
    left.
    """
    dated = [
        (parse_date(m.get("date")), m)
        for m in record.get("milestones") or []
        if isinstance(m, dict)
        and m.get("role") == role
        and not (skip_passed and m.get("passed"))
    ]
    dated = [(date, m) for date, m in dated if date is not None]
    if not dated:
        return None
    # Compare dates only: two milestones are never compared with each other.
    return pick(dated, key=lambda pair: pair[0])[1]


def phase_status_line(record):
    """The sentence at the top of a banner, for the record's (stored) phase.

    The dates come from the milestones that decide the phase: the earliest
    "opens", the next "deadline" that has not passed (a call with two deadlines
    shows the first until it passes, then the second), the latest "results" and
    the earliest "next". They are written the way the milestone list shows
    them (``date_text``, so a ``display_date`` such as "March 2027" is used as
    written). If the milestone a phase needs is missing,
    that part of the sentence is left out rather than printing a blank or
    "None". Returns "" when nothing is left to say.
    """
    phase = record.get("phase")

    if phase == "upcoming":
        opens = _milestone_with_role(record, "opens", min)
        return f"Opens {milestone_date_text(opens)}" if opens else ""

    if phase == "open":
        # An open call has at least one deadline still ahead (it stays open
        # through the last one), so this finds the next one to meet.
        deadline = _milestone_with_role(record, "deadline", min, skip_passed=True)
        return f"Deadline {milestone_date_text(deadline)}" if deadline else ""

    if phase == "in_review":
        sentence = "Submissions closed; review in progress"
        results = _milestone_with_role(record, "results", max)
        if results:
            sentence += f". Results expected {milestone_date_text(results)}"
        return sentence

    if phase == "closed":
        sentence = "Closed"
        next_call = _milestone_with_role(record, "next", min)
        if next_call:
            sentence += f". Next opportunity expected {milestone_date_text(next_call)}"
        return sentence

    return ""
