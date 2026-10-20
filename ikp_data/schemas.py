"""Pydantic models describing every YAML record under docs/contribution-types/_data/.

Why this file exists
--------------------
Until now the only definition of "a valid card" was whatever the page loaders happened to
tolerate. These models make that definition explicit, so that a typo in a key,
a missing date, or a stray personal e-mail address is caught when the YAML is
edited rather than discovered on the published page.

How to read it
--------------
* There is one model per record type: ``Telescope``, ``Opportunity``,
  ``Dataset``, ``Software`` and ``Idac``, plus small nested models.
* The models describe the YAML *as written in the files* (what
  ``yaml.safe_load`` returns). They must never be applied to the enriched
  dictionaries that the loaders (``ikp_data.loaders``) build, because those carry extra derived keys
  (``slug``, ``status``, ``filter_tokens``, ...) that the models forbid.
* Every model forbids unknown keys (``extra="forbid"``). That is how a typo, or
  a key that must not be stored, is rejected.
* Every field carries two pieces of metadata:

  - ``description``: plain-language help text, suitable for a form or tooltip;
  - ``json_schema_extra={"rendered": bool}``: whether the field appears on, or
    affects, the public page. (Fields that only steer the page, such as a
    status override or ``visible_until``, count as rendered.)
  - ``json_schema_extra={"content_update": bool}`` (optional, defaults to the
    value of ``rendered``): whether changing the field should by default count
    as a content update that bumps the card's ``last_updated`` date. Highlight
    fields are rendered but set ``content_update`` to False, because adding or
    expiring a highlight does not change the card's content.

  Read the flags back with ``Model.model_fields["name"].json_schema_extra``, or
  use ``counts_as_content_update(field_info)`` for the content-update answer.

Submitter personal information
------------------------------
Form submissions can include the submitter's name and e-mail address. Those must
never be committed to this public repository. The forbidden keys are
deliberately *not declared* anywhere below, so ``extra="forbid"`` rejects them;
``_RejectSubmitterPii`` additionally gives a message that names the problem.
"""

from __future__ import annotations

import datetime
import re
from typing import Annotated, Any, Literal, Union

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)

# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _field(
    description: str,
    *,
    rendered: bool,
    content_update: bool | None = None,
    default: Any = ...,
    default_factory: Any = None,
    **constraints: Any,
) -> Any:
    """Build a ``Field`` that always carries a description and a rendered flag.

    ``content_update`` is stored only when given; leave it out to inherit the
    value of ``rendered`` (see the module docstring).

    ``default=...`` (the default) means the field is required. Pass
    ``default=None`` for an optional field, or ``default_factory=list`` for a
    list that defaults to empty. Any extra keyword (``ge=``, ``le=``) is passed
    straight to ``Field``.
    """
    extra: dict[str, bool] = {"rendered": rendered}
    if content_update is not None:
        extra["content_update"] = content_update
    if default_factory is not None:
        return Field(
            default_factory=default_factory,
            description=description,
            json_schema_extra=extra,
            **constraints,
        )
    return Field(
        default,
        description=description,
        json_schema_extra=extra,
        **constraints,
    )


def counts_as_content_update(field_info: Any) -> bool:
    """Return True if changing this field should default to a content update.

    Uses the optional ``content_update`` flag, falling back to ``rendered``.
    """
    extra = field_info.json_schema_extra or {}
    return bool(extra.get("content_update", extra["rendered"]))


def _check_iso_date_string(value: str) -> str:
    """Accept only a real calendar date written exactly as ``YYYY-MM-DD``."""
    if not _ISO_DATE_PATTERN.match(value):
        raise ValueError(
            f"{value!r} is not in YYYY-MM-DD form (two-digit month and day, "
            "for example '2026-07-22')"
        )
    try:
        datetime.date.fromisoformat(value)
    except ValueError as err:
        raise ValueError(f"{value!r} is not a valid calendar date: {err}") from err
    return value


def _reject_unquoted_date(value: Any) -> Any:
    """Give a helpful message when YAML turned an unquoted date into a date object.

    ``last_updated: 2026-07-22`` (no quotes) is parsed by YAML as a date, not a
    string, which would then sort and compare differently from the quoted
    strings used everywhere else. Ask for quotes instead of silently coercing.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        raise ValueError(
            f"{value.isoformat()} was read as a YAML date; quote it "
            f"(for example '{value.isoformat()[:10]}') so it stays a string"
        )
    return value


# A date stored as a quoted ISO string: 'YYYY-MM-DD'. Used for ``last_updated``
# and ``curated.highlight.until``.
IsoDateString = Annotated[
    str,
    BeforeValidator(_reject_unquoted_date),
    AfterValidator(_check_iso_date_string),
]


def _check_date_or_iso_string(value: Any) -> Any:
    """Validate a date that may be a quoted ISO string or an unquoted YAML date.

    The loaders accept either form for ``visible_until`` and milestone ``date``
    (they convert strings with ``datetime.date.fromisoformat``). Real files use
    quoted strings, which is the preferred form.
    """
    if isinstance(value, datetime.datetime):
        raise ValueError("a date is expected here, not a date with a time")
    if isinstance(value, datetime.date):
        return value
    return _check_iso_date_string(value)


# A date written as a quoted ISO string (preferred) or as a YAML date.
IsoDateOrDate = Annotated[
    Union[datetime.date, str],
    AfterValidator(_check_date_or_iso_string),
]


class _Strict(BaseModel):
    """Base class for every record model: unknown keys are errors, not ignored."""

    model_config = ConfigDict(extra="forbid")


class Link(_Strict):
    """A labelled hyperlink, used for opportunity links and facility links."""

    label: str = _field("Text shown for the link.", rendered=True)
    url: str = _field("Full address of the link, starting with https://.", rendered=True)


# ---------------------------------------------------------------------------
# Telescopes (docs/contribution-types/_data/telescopes/*.yaml)
# ---------------------------------------------------------------------------

TelescopeStatus = Literal["available", "future_semester", "past_opportunity"]


class TelescopeContact(_Strict):
    """A person visitors can contact about a facility."""

    name: str = _field("Contact person's name.", rendered=True)
    email: str = _field("Contact e-mail address (published on the page).", rendered=True)
    note: str | None = _field(
        "Optional note shown with the contact, for example who to ask about what.",
        rendered=False,
        default=None,
    )


class Telescope(_Strict):
    """One facility card on the Contributed Telescopes page.

    A facility that is contributed together with others (for example the three
    KMTNet sites) shares its ``contribution_id`` with its siblings, so
    ``contribution_id`` is not unique per file. A facility funded jointly by two
    contributions lists both IDs.
    """

    contribution_id: str | list[str] = _field(
        "In-kind contribution ID, for example 'KOR-KAS-S2'. Use a list when one "
        "facility is contributed under several IDs.",
        rendered=True,
    )
    facility: str = _field("Facility name shown as the card title.", rendered=True)
    aperture: str = _field(
        "Primary mirror size as text, for example '10.4m'. Also used for the aperture filter.",
        rendered=True,
    )
    country: str = _field("Country of the contributing partner.", rendered=True)
    site: str = _field("Observatory or site name.", rendered=True)
    latitude: float = _field(
        "Site latitude in decimal degrees (north positive). Needed to place the map marker.",
        rendered=True,
        ge=-90,
        le=90,
    )
    longitude: float = _field(
        "Site longitude in decimal degrees (east positive). Needed to place the map marker.",
        rendered=True,
        ge=-180,
        le=180,
    )
    instrumentation: list[str] = _field(
        "Kinds of instrument available, for example 'Imaging' or 'Spectroscopy'.",
        rendered=True,
        default_factory=list,
    )
    instrument_names: list[str] = _field(
        "Names of the individual instruments.", rendered=True, default_factory=list
    )
    wavelength_regime: list[str] = _field(
        "Wavelength regimes covered, for example 'Optical' or 'NIR'.",
        rendered=True,
        default_factory=list,
    )
    spectral_resolution_min: float | None = _field(
        "Lowest spectral resolution R offered (drives the resolution filter), or empty if unknown.",
        rendered=True,
        default=None,
    )
    spectral_resolution_max: float | None = _field(
        "Highest spectral resolution R offered (drives the resolution filter), or empty if unknown.",
        rendered=True,
        default=None,
    )
    multiplex: bool | None = _field(
        "True if the facility can observe many objects at once (shows a Multiplex badge).",
        rendered=True,
        default=None,
    )
    field_of_view: str | None = _field(
        "Field of view as text. Stored but not currently shown on the page.",
        rendered=False,
        default=None,
    )
    aeon: bool | None = _field(
        "True if the facility is reachable through the AEON observing network (shows an AEON badge).",
        rendered=True,
        default=None,
    )
    too_capable: bool | None = _field(
        "True if the facility can take target-of-opportunity observations (shows a ToO badge).",
        rendered=True,
        default=None,
    )
    observing_mode: str | None = _field(
        "Observing mode, for example 'queue', 'service' or 'mixed'. Stored but not shown on the page.",
        rendered=False,
        default=None,
    )
    contacts: list[TelescopeContact] = _field(
        "People to contact about this facility.", rendered=True, default_factory=list
    )
    first_semester: str = _field(
        "First semester the facility is available, for example '2026A', or 'TBA'.",
        rendered=True,
    )
    time_available: str = _field(
        "How much time is offered, for example '2 nights/semester'.", rendered=True
    )
    duration: str = _field(
        "How long the contribution lasts, for example '10 years'.", rendered=True
    )
    status: TelescopeStatus = _field(
        "Availability: 'available' now, 'future_semester', or 'past_opportunity'. "
        "Controls the badge, the status filter and the card order.",
        rendered=True,
    )
    tac_process: str = _field(
        "How time is allocated, for example 'special' for a dedicated call. Only used "
        "for consistency checks between sibling facilities; not shown on the page.",
        rendered=False,
    )
    external_links: list[Link] = _field(
        "Links to the facility's own pages.", rendered=True, default_factory=list
    )
    summary: str = _field("Short description shown on the card.", rendered=True)


# ---------------------------------------------------------------------------
# Opportunities (docs/contribution-types/_data/opportunities/*.yaml)
# ---------------------------------------------------------------------------

MilestoneRole = Literal["opens", "deadline", "results", "next"]
Accent = Literal["warning"]


class Milestone(_Strict):
    """A dated step in an opportunity, for example a submission deadline."""

    label: str = _field("What happens on this date.", rendered=True)
    date: IsoDateOrDate = _field(
        "The date as a quoted ISO string, 'YYYY-MM-DD'. Used for ordering and for "
        "deciding when the opportunity is current.",
        rendered=True,
    )
    display_date: str | None = _field(
        "Text shown instead of the exact date, for example 'Feb 2027', when the "
        "date is only approximate.",
        rendered=True,
        default=None,
    )
    approximate: bool | None = _field(
        "True if the date is an estimate (adds '(approx.)' on the page).",
        rendered=True,
        default=None,
    )
    role: MilestoneRole | None = _field(
        "Optional meaning of this milestone: 'opens' (call opens), 'deadline' "
        "(submission deadline; the last one counts), 'results' (decisions "
        "announced) or 'next' (next expected opportunity). Leave empty for "
        "purely informational milestones.",
        rendered=False,
        default=None,
    )
    passed: bool | None = _field(
        "DEPRECATED. Hand-set 'this date has passed' flag that currently adds a "
        "strike-through. It will be computed from the date once the template does "
        "so, and then removed; do not add it to new records.",
        rendered=True,
        default=None,
    )


class Opportunity(_Strict):
    """A call or special opportunity banner at the top of the Telescopes page.

    The old ``contact`` block is intentionally not declared: it was never shown
    on the page and is being removed from the data.
    """

    id: str = _field(
        "Short unique name for the opportunity; matches the file name.", rendered=False
    )
    title: str = _field("Headline of the opportunity card.", rendered=True)
    kind: str = _field(
        "Type of opportunity, for example 'special_call' or 'general_cfp'.",
        rendered=False,
    )
    accent: Accent | None = _field(
        "Optional highlight style for the card; only 'warning' exists today.",
        rendered=True,
        default=None,
    )
    related_contribution_ids: list[str] = _field(
        "Contribution IDs of the facilities this opportunity relates to; each "
        "becomes a link to that facility's card.",
        rendered=True,
        default_factory=list,
    )
    summary: str = _field("Short description shown on the card.", rendered=True)
    milestones: list[Milestone] = _field(
        "Dated steps of the opportunity.", rendered=True, default_factory=list
    )
    links: list[Link] = _field(
        "Links to the announcement and related pages.", rendered=True, default_factory=list
    )
    visible_until: IsoDateOrDate = _field(
        "Last day the card is shown (a quoted ISO date). After this day the card "
        "disappears from the page at the next site build.",
        rendered=True,
    )


# ---------------------------------------------------------------------------
# Datasets (docs/contribution-types/_data/datasets/*.yaml)
# ---------------------------------------------------------------------------

DatasetStatus = Literal["available", "not_yet_delivered"]


# Keys the submission forms could produce that identify the submitter.
_FORBIDDEN_PII_KEYS = ("email", "submitter_name", "name")


class _RejectSubmitterPii(_Strict):
    """Base for form_data models: give a clear message for submitter PII keys.

    The submission form collects the submitter's name and e-mail address. They
    belong in the private form-response spreadsheet only. They are not declared
    as fields, so ``extra="forbid"`` would already reject them; this validator
    adds an explicit explanation so nobody has to guess why.
    """

    @model_validator(mode="before")
    @classmethod
    def _reject_pii_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            found = [key for key in _FORBIDDEN_PII_KEYS if key in data]
            if found:
                names = ", ".join(f"form_data.{key}" for key in found)
                raise ValueError(
                    f"{names}: submitter personal information must not be stored "
                    "in this public repository; delete the key"
                )
        return data


class DatasetFormData(_RejectSubmitterPii):
    """Details supplied through the dataset submission form.

    The sync script owns this block and may overwrite it, so do not hand-edit it
    for permanent changes. Software records can embed the same block as
    ``associated_dataset``.
    """

    submitted: bool = _field(
        "True once the contributor has submitted the dataset form; decides "
        "whether the card reads 'Available' (unless overridden in curated).",
        rendered=True,
    )
    data_type: list[str] = _field(
        "Kinds of data, for example 'Catalog' or 'Images' (badges and filter).",
        rendered=True,
        default_factory=list,
    )
    uat_category: list[str] = _field(
        "Unified Astronomy Thesaurus categories (badges and filter).",
        rendered=True,
        default_factory=list,
    )
    uat_concepts: str | None = _field(
        "Specific UAT concepts, as free text. Not shown on the page.",
        rendered=False,
        default=None,
    )
    target_audience: str | None = _field(
        "Who the dataset is for, as written by the contributor (used if the curated "
        "value is empty).",
        rendered=True,
        default=None,
    )
    contribution_summary: str | None = _field(
        "Summary as written by the contributor; used to seed the curated summary. "
        "Not shown directly.",
        rendered=False,
        default=None,
    )
    version: str | None = _field(
        "Dataset version, as given by the contributor. Not shown on the page.",
        rendered=False,
        default=None,
    )
    data_volume: str | None = _field("Size of the dataset.", rendered=True, default=None)
    hosting_location: str | None = _field(
        "Where the data are hosted.", rendered=True, default=None
    )
    access_url: str | None = _field(
        "Where to get the data (address or instructions).", rendered=True, default=None
    )
    access_mechanisms: list[str] = _field(
        "Ways to access the data, for example 'API' or 'TAP / Virtual Observatory Service'.",
        rendered=True,
        default_factory=list,
    )
    authentication: str | None = _field(
        "Whether a login is needed and how to get one.", rendered=True, default=None
    )
    data_schema_link: str | None = _field(
        "Link to the data schema or format description.", rendered=True, default=None
    )
    generation_methods: str | None = _field(
        "How the data were produced.", rendered=True, default=None
    )
    validation_limitations: str | None = _field(
        "How the data were validated and known limitations.", rendered=True, default=None
    )
    tutorials_docs: str | None = _field(
        "Documentation and tutorials.", rendered=True, default=None
    )
    support_channel: str | None = _field(
        "Where users can get help.", rendered=True, default=None
    )
    citation: str | None = _field(
        "How to cite the dataset.", rendered=True, default=None
    )
    maintenance_plan: str | None = _field(
        "Plan for keeping the dataset available and up to date.",
        rendered=True,
        default=None,
    )
    maintenance_notes: str | None = _field(
        "Additional maintenance notes. Not shown on the page.",
        rendered=False,
        default=None,
    )
    final_report: str | None = _field(
        "Link to the contributor's final report. Not shown on the page.",
        rendered=False,
        default=None,
    )


class Highlight(_Strict):
    """A temporary 'featured' marker for a dataset or software card.

    A highlighted card appears in a teaser row until ``until`` has passed.
    """

    reason: str = _field(
        "Short badge text explaining the highlight, for example 'Newly delivered'.",
        rendered=True,
        content_update=False,
    )
    until: IsoDateString = _field(
        "Last day the highlight is active, as a quoted ISO date 'YYYY-MM-DD'.",
        rendered=True,
        content_update=False,
    )


class DatasetCurated(_Strict):
    """Hand-edited fields of a dataset record; the sync script never overwrites them."""

    primary_recipient: str | None = _field(
        "The main group the dataset is intended for.", rendered=True, default=None
    )
    target_audience: str | None = _field(
        "Who the dataset is for; takes precedence over the form's value.",
        rendered=True,
        default=None,
    )
    summary: str | None = _field(
        "Short description shown on the card ('TBD' appears if empty).",
        rendered=True,
        default=None,
    )
    wavelength_regime: list[str] = _field(
        "Wavelength regimes covered, for example 'Optical' (badges and filter).",
        rendered=True,
        default_factory=list,
    )
    status_override: DatasetStatus | None = _field(
        "Force the card status instead of deriving it from the form: "
        "'available' or 'not_yet_delivered'. Leave empty normally.",
        rendered=True,
        default=None,
    )
    related_contribution_ids: list[str] = _field(
        "IDs of related contributions (for example the software that produced "
        "the data); each becomes an 'Also see' link.",
        rendered=True,
        default_factory=list,
    )
    needs_review: bool | None = _field(
        "Reminder flag set on new cards. Not shown on the page.",
        rendered=False,
        default=None,
    )
    highlight: Highlight | None = _field(
        "Optional temporary highlight for this card.",
        rendered=True,
        content_update=False,
        default=None,
    )


class Dataset(_Strict):
    """One dataset card on the Contributed Datasets page."""

    contribution_id: str = _field(
        "In-kind contribution ID, for example 'CHL-UCH-D1'; unique among datasets.",
        rendered=True,
    )
    title: str = _field("Dataset title.", rendered=True)
    country: str | None = _field("Contributing country.", rendered=True, default=None)
    institute: str | None = _field(
        "Contributing institute. Stored but not shown on the page.",
        rendered=False,
        default=None,
    )
    last_updated: IsoDateString = _field(
        "Date the card's content last changed, as a quoted ISO date 'YYYY-MM-DD'. "
        "Shown as 'Updated' on the card and used for ordering.",
        rendered=True,
    )
    form_data: DatasetFormData = _field(
        "Details from the submission form.", rendered=True
    )
    curated: DatasetCurated = _field("Hand-edited fields.", rendered=True)


# ---------------------------------------------------------------------------
# Software (docs/contribution-types/_data/software/*.yaml)
# ---------------------------------------------------------------------------

SoftwareStatus = Literal["delivered", "pending"]


class SoftwareFormData(_RejectSubmitterPii):
    """Details supplied through the software submission form (sync-owned)."""

    submitted: bool = _field(
        "True once the contributor has submitted the software form; decides "
        "whether the card reads 'Delivered' (unless overridden in curated).",
        rendered=True,
    )
    category: str | None = _field(
        "Contribution category, for example 'Directable SW dev'.",
        rendered=True,
        default=None,
    )
    primary_recipient_group: str | None = _field(
        "The main Rubin group the software is intended for.",
        rendered=True,
        default=None,
    )
    additional_recipient_groups: list[str] = _field(
        "Other groups that will use the software.", rendered=True, default_factory=list
    )
    activity_description: str | None = _field(
        "Description of the software development activity (main card text).",
        rendered=True,
        default=None,
    )
    timeline: str | None = _field(
        "Planned timeline; a fiscal year in it sets the approximate start shown.",
        rendered=True,
        default=None,
    )
    software_name: str | None = _field(
        "Name of the software product.", rendered=True, default=None
    )
    software_url: str | None = _field(
        "Where to find the software; links are extracted for the card.",
        rendered=True,
        default=None,
    )
    documentation: str | None = _field(
        "Where to find the documentation; links are extracted for the card.",
        rendered=True,
        default=None,
    )
    uat_category: list[str] | None = _field(
        "Unified Astronomy Thesaurus categories from the form; replace the curated "
        "keywords when present.",
        rendered=True,
        default=None,
    )
    uat_concepts: str | None = _field(
        "Specific UAT concepts, as free text. Not shown on the page.",
        rendered=False,
        default=None,
    )
    target_audience: str | None = _field(
        "Intended audience. Not shown on the page.", rendered=False, default=None
    )
    acknowledgements: str | None = _field(
        "Acknowledgements text. Not shown on the page.", rendered=False, default=None
    )
    publications: str | None = _field(
        "Related publications. Not shown on the page.", rendered=False, default=None
    )
    sharing_of_software: str | None = _field(
        "How the software will be shared. Not shown on the page.",
        rendered=False,
        default=None,
    )
    verification_testing: str | None = _field(
        "Testing and verification approach. Not shown on the page.",
        rendered=False,
        default=None,
    )
    support: str | None = _field(
        "Support arrangements. Not shown on the page.", rendered=False, default=None
    )
    further_development: str | None = _field(
        "Plans for further development. Not shown on the page.",
        rendered=False,
        default=None,
    )
    maintenance_plan: str | None = _field(
        "Maintenance plan. Not shown on the page.", rendered=False, default=None
    )
    maintenance_notes: str | None = _field(
        "Additional maintenance notes. Not shown on the page.",
        rendered=False,
        default=None,
    )
    other_feedback: str | None = _field(
        "Other feedback from the contributor. Not shown on the page.",
        rendered=False,
        default=None,
    )
    version: str | None = _field(
        "Software version. Not shown on the page.", rendered=False, default=None
    )
    associated_dataset: DatasetFormData | None = _field(
        "Dataset details when the contribution also delivers a dataset. Not shown "
        "on this page; the companion dataset card shows them.",
        rendered=False,
        default=None,
    )


class SoftwareCurated(_Strict):
    """Hand-edited fields of a software record; the sync script never overwrites them."""

    uat_keywords: list[str] = _field(
        "Keyword tags (badges and filter) used when the form gave no UAT categories.",
        rendered=True,
        default_factory=list,
    )
    summary: str | None = _field(
        "Optional curated summary. Not shown on the page today.",
        rendered=False,
        default=None,
    )
    status_override: SoftwareStatus | None = _field(
        "Force the card status instead of deriving it from the form: 'delivered' "
        "or 'pending'. Leave empty normally.",
        rendered=True,
        default=None,
    )
    related_contribution_ids: list[str] = _field(
        "IDs of related datasets or facilities; each becomes an 'Also see' link.",
        rendered=True,
        default_factory=list,
    )
    needs_review: bool | None = _field(
        "Reminder flag set on new cards. Not shown on the page.",
        rendered=False,
        default=None,
    )
    highlight: Highlight | None = _field(
        "Optional temporary highlight for this card.",
        rendered=True,
        content_update=False,
        default=None,
    )


class Software(_Strict):
    """One software card on the Contributed Software page."""

    contribution_id: str = _field(
        "In-kind contribution ID, for example 'CHL-UCH-S3'; unique among software.",
        rendered=True,
    )
    title: str = _field("Software contribution title.", rendered=True)
    country: str | None = _field(
        "Contributing country. Stored but not shown on the page.",
        rendered=False,
        default=None,
    )
    institute: str | None = _field(
        "Contributing institute. Stored but not shown on the page.",
        rendered=False,
        default=None,
    )
    last_updated: IsoDateString = _field(
        "Date the card's content last changed, as a quoted ISO date 'YYYY-MM-DD'. "
        "Shown as 'Updated' on the card and used for ordering.",
        rendered=True,
    )
    form_data: SoftwareFormData = _field(
        "Details from the submission form.", rendered=True
    )
    curated: SoftwareCurated = _field("Hand-edited fields.", rendered=True)


# ---------------------------------------------------------------------------
# IDACs (docs/contribution-types/_data/idacs/*.yaml)
# ---------------------------------------------------------------------------

Number = Union[int, float]


class IdacLocation(_Strict):
    """Where an IDAC is hosted."""

    city: str = _field("City.", rendered=True)
    institution: str = _field("Hosting institution.", rendered=True)
    lat: float = _field("Latitude in decimal degrees.", rendered=True, ge=-90, le=90)
    lng: float = _field("Longitude in decimal degrees.", rendered=True, ge=-180, le=180)


class IdacDataProducts(_Strict):
    """Which Rubin data products an IDAC will host (true or false for each)."""

    object_table_subset: bool = _field("Hosts a subset of the Object table.", rendered=True)
    object_table: bool = _field("Hosts the Object table.", rendered=True)
    source_table: bool = _field("Hosts the Source table.", rendered=True)
    forced_source_table: bool = _field("Hosts the ForcedSource table.", rendered=True)
    dia_object_table: bool = _field("Hosts the DIAObject table.", rendered=True)
    dia_source_table: bool = _field("Hosts the DIASource table.", rendered=True)
    solar_system_tables: bool = _field("Hosts the Solar System tables.", rendered=True)
    co_added_images: bool = _field("Hosts co-added images.", rendered=True)
    visit_images: bool = _field("Hosts visit images.", rendered=True)
    difference_images: bool = _field("Hosts difference images.", rendered=True)
    template_images: bool = _field("Hosts template images.", rendered=True)
    other_data_products: bool = _field("Hosts other data products.", rendered=True)


class IdacCapacity(_Strict):
    """Capacity over the 13-year IDAC lifetime. Empty means 'to be determined'."""

    storage_pb_years: Number | None = _field(
        "Storage in petabyte-years.", rendered=True, default=None
    )
    free_storage_pb_years: Number | None = _field(
        "Storage in petabyte-years offered free to the community. Not shown on the page.",
        rendered=False,
        default=None,
    )
    cpu_mhrs: Number | None = _field("CPU in million hours.", rendered=True, default=None)
    free_cpu_mhrs: Number | None = _field(
        "CPU offered free, in million hours. Not shown on the page.",
        rendered=False,
        default=None,
    )
    gpu_mhrs: Number | None = _field("GPU in million hours.", rendered=True, default=None)
    free_gpu_mhrs: Number | None = _field(
        "GPU offered free, in million hours. Not shown on the page.",
        rendered=False,
        default=None,
    )
    hosted_data_pb_years: Number | None = _field(
        "Hosted data volume in petabyte-years. Not shown on the page.",
        rendered=False,
        default=None,
    )
    expected_local_users: Number | None = _field(
        "Expected number of local users.", rendered=True, default=None
    )


class IdacHardware(_Strict):
    """Free-text description of the hardware."""

    cpu_architecture: str = _field("CPU architecture.", rendered=True)
    gpu_architecture: str = _field("GPU architecture.", rendered=True)
    storage_type: str = _field("Storage type.", rendered=True)
    network: str = _field("Network.", rendered=True)


class IdacContact(_Strict):
    """A contact person for an IDAC."""

    name: str = _field("Contact person's name.", rendered=True)
    email: str = _field("Contact e-mail address (published on the page).", rendered=True)
    role: str | None = _field(
        "Contact's role. Not shown on the page.", rendered=False, default=None
    )


class IdacDocumentationLink(_Strict):
    """A documentation link for an IDAC; an empty ``url`` means 'not provided yet'."""

    title: str = _field("Link text.", rendered=True)
    url: str = _field("Address of the page; may be empty until provided.", rendered=True)


class Idac(_Strict):
    """One Rubin Independent Data Access Center (IDAC) entry on the Resources page."""

    country: str = _field("Country of the IDAC.", rendered=True)
    slug: str = _field(
        "Short lowercase name used in the page address and anchors.", rendered=True
    )
    idac_type: str = _field(
        "Kind of center, for example 'Lite IDAC'; drives the type filter and marker colour.",
        rendered=True,
    )
    location: IdacLocation = _field("Where the IDAC is hosted.", rendered=True)
    data_products: IdacDataProducts = _field(
        "Rubin data products hosted.", rendered=True
    )
    data_releases: list[str] = _field(
        "Data releases stored, for example ['DP1', 'DR1']; empty if to be determined.",
        rendered=True,
        default_factory=list,
    )
    capacity: IdacCapacity = _field("Capacity figures.", rendered=True)
    hardware: IdacHardware = _field("Hardware description.", rendered=True)
    software_services: str = _field(
        "Software and services offered.", rendered=True
    )
    complementary_datasets: str = _field(
        "Other datasets hosted alongside Rubin data.", rendered=True
    )
    use_cases: str = _field("Science use cases the IDAC specializes in.", rendered=True)
    science_collaboration_agreements: str = _field(
        "Agreements with Rubin science collaborations.", rendered=True
    )
    documentation: list[IdacDocumentationLink] = _field(
        "Onboarding and documentation links.", rendered=True, default_factory=list
    )
    contacts: list[IdacContact] = _field(
        "Contact people.", rendered=True, default_factory=list
    )
    notes: str = _field("Free-text notes.", rendered=True)


# ---------------------------------------------------------------------------
# Lookup used by the validator: data sub-folder name -> model
# ---------------------------------------------------------------------------

MODEL_FOR_FOLDER: dict[str, type[_Strict]] = {
    "telescopes": Telescope,
    "opportunities": Opportunity,
    "datasets": Dataset,
    "software": Software,
    "idacs": Idac,
}
