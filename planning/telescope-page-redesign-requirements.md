# Contributed Telescope Access page redesign — requirements

**Repo:** `lsst/in-kind-program_lsst_io`
**Target file:** `docs/contribution-types/contributed-telescope.rst`
**Model:** `docs/contribution-types/contributed-datasets.rst` (shipped card/filter redesign, PR #37)
**Author:** drafted for Steve Margheim, In-kind Program coordinator, NOIRLab
**Status:** draft — open items below need sign-off before implementation starts

## 1. Goal

Replace the current static reST grid table + prose-section layout on the Contributed Telescope Access page with a filterable, card-based layout matching the Contributed Datasets page, so NOIRLab community members can quickly find telescope time relevant to their science case (by instrument type, location, status, aperture) instead of scanning a 15-row table and two blocks of prose.

## 2. Current state

- One giant reST grid table (facility, location, instrumentation, contribution ID, first semester, time available, duration) — hand-maintained, hard to scan on mobile, no sorting or filtering.
- Two prose sections, "Now Available" and "Available in a Future Semester", each a subsection per contribution ID, manually kept in sync with the table.
- No per-record data file — everything lives inline in the `.rst` file. Any update means editing reST table cell widths by hand.
- No filtering, search, or status toggle.
- Two data inconsistencies found while reviewing current content, to fix during migration:
  - The Milankovic Telescope table row's contribution ID (`SER-SAG-S2`) doesn't match its prose section heading and anchor (`SER-SAG-S1`) — need to confirm the correct ID.
  - "Milankovic Telescope 1.4m Telescope 1.4m" has a duplicated "Telescope 1.4m" in the facility name cell.

## 3. Reference architecture (Contributed Datasets page)

- Per-contribution YAML files at `docs/contribution-types/_data/datasets/<contribution-id>.yaml`, each split into:
  - `form_data`: fields owned by an external CSV-pull script tied to a contributor intake form (safe to overwrite on sync).
  - `curated`: hand-edited-only fields (summary, wavelength regime, status override).
- `conf.py` has a loader (`_load_contributed_datasets`) that reads every YAML file at build time, computes a slug, a `status` (derived from `form_data.submitted` unless `curated.status_override` is set), a `last_updated` date (from git log, falling back to file mtime), a set of CSS-safe `filter_tokens`, and a lowercased `search_text` blob. It exposes all of this plus the distinct filter values (`all_data_types`, `all_wavelengths`, `all_uat`) through `jinja_contexts["contributed_datasets"]`.
- `contributed-datasets.rst` uses a `.. jinja:: contributed_datasets` block containing: inline CSS, a filter bar (three `<select>` dropdowns), a search box + "show available only" toggle, a sortable HTML `<table>` summary, a vanilla-JS filter/sort/search script, and a `sphinx-design` `.. grid::` of `.. grid-item-card::` blocks (one Jinja loop, split into "available" vs "not yet delivered" card bodies).
- No build tooling beyond Sphinx + `documenteer[guide]` (which bundles `sphinx-design`, `sphinx-jinja`, etc.) — no separate JS/CSS pipeline.

**Important difference for telescopes:** there is no external intake form or CSV-pull process for telescope facility data — the In-kind coordinator is the sole source of truth. The `form_data`/`curated` split exists on the datasets page specifically to protect hand-edited fields from being clobbered by that sync; telescopes have no such sync process today.

## 4. Decisions already made

- **Multi-facility contribution IDs:** three contribution IDs cover more than one physical facility today (`KOR-KAS-S2` → 3 KMTNet sites, near-identical aside from location; `NZL-AUK-S1` → Nishimura 1.8m + McLellan 1.0m at Mt John; `ITA-INA-S18` → VST + LBT, which are materially different facilities). Decision: **each physical facility gets its own card**, but cards that share a contribution ID are visibly tied together (e.g. a shared badge/cross-link, "part of the same contribution as: ..."). The current table is already at this granularity (14 rows = 14 facilities), so no row-splitting is needed — this is a rendering/grouping requirement on top of data that's already right.
- **GTC (ESP-BCM-S5 + ESP-IAC-S1):** the reverse case — one facility, two contribution IDs — is resolved as **a single card**. The two IDs act as one contribution (Barcelona-Madrid + IAC jointly funding the same ~2 nights/semester on GTC), so `contribution_id` on the GTC record is list-valued (`[ESP-BCM-S5, ESP-IAC-S1]`) rather than being split into two cards.

## 5. Open items — need your sign-off

These are proposed defaults, not committed. Flag anything you want changed.

| # | Question | Recommended default |
|---|---|---|
| 1 | ~~Status model.~~ | **Resolved: single hand-set `status` field per record (`available` / `future_semester` / `tba`), no `form_data`/`curated` split** — flat schema, coordinator edits directly. |
| 2 | ~~Filter facets.~~ | **Resolved: Instrumentation type, Wavelength regime, Spectral resolution (explicit numeric bins, e.g. "R < 1,000" / "1,000 ≤ R < 5,000" / "R ≥ 5,000" — labels state the number, not an adjective), Multiplex (yes/no), Status, Hemisphere (derived), Aperture band (<2m, 2–8m, >8m).** Field of view stays informational/card-only, not a filter. |
| 3 | ~~Grouping mechanism for shared contribution IDs.~~ | **Resolved: each facility gets its own full card; cards sharing a `contribution_id` carry a small "Also available under this contribution:" cross-link list.** The contribution-level narrative (currently one shared paragraph per ID) is stored once and referenced by all sibling records rather than copy-pasted. |
| 4 | ~~SER-SAG-S1 vs. SER-SAG-S2.~~ | **Resolved: `SER-SAG-S2`** is correct. The prose section heading/anchor on the current page (`SER-SAG-S1`) is the typo and will be fixed during migration. |
| 5 | ~~Map rendering approach.~~ | **Resolved: inline static SVG**, no external tile/network dependency. Precise on-mountain zoom isn't useful for discovery anyway — rough lat/long is enough to gauge feasibility (hemisphere, region), so Leaflet's real pan/zoom wasn't worth the added dependency. Clustered markers (SAAO, Mt John) get simple positional offsetting rather than real zoom-to-separate. Filtering and click-to-scroll-to-card work the same as the static approach either way — that's JS reusing the existing `filter_tokens` mechanism, not a map-library feature. |
| 6 | ~~Build freshness for time-sensitive opportunities.~~ | **Resolved: no scheduled rebuild needed.** Opportunities change on months-long cycles; the existing on-push build is sufficient since a manual content edit (adding/removing/expiring an opportunity) will naturally trigger a rebuild at the right time. |
| 7 | ~~AEON/ToO display when unknown or false.~~ | **Resolved: nullable booleans, badge shown only when true.** No "AEON: unknown" clutter while most facilities' data is still being filled in. |
| 8 | ~~Hemisphere: derived or hand-authored?~~ | **Resolved: derived from `latitude`'s sign** in the `conf.py` loader, not a stored field. |
| 9 | ~~Instrumentation detail level.~~ | **Resolved: coarse controlled-vocabulary `instrumentation` (for filtering) plus an optional free-text `instrument_names` list** (e.g. GTC's OSIRIS+, EMIR, MEGARA, HiPERCAM) shown in the card body when known. |
| 10 | ~~Additional discovery fields.~~ | **Resolved (Section 6.1): add `wavelength_regime`, `spectral_resolution_min/max` (explicit R numbers, not low/medium/high labels), `multiplex` (yes/no), and `field_of_view`.** Science-case/UAT tagging and Rubin-survey-affinity tagging were considered and explicitly rejected — discovery here is capability-based, not science-based; UAT categories are too broad across facilities to discriminate usefully. |
| 11 | **Status model** (never actually re-confirmed after the initial proposal). Single hand-set `status` field, no `form_data`/`curated` split. | Still just the original recommended default — needs an explicit yes/no from you, unlike items 2–10 which were revisited. |
| 12 | **AEON status for LBT, VST, and NOT** is still `not documented`. All three had ToO confirmed from the 2026B CfP text, but AEON specifically was never asked about and got missed by the facility-review queue. | Need your input — same treatment as the other AEON/ToO gaps. |
| 13 | **Nishimura 1.8m's "tentative yes" on AEON/ToO** needs to convert to a firm answer before this ships — currently the only facility with a provisional rather than confirmed value. | Track as blocking final content sign-off, not blocking the implementation build itself. |
| 14 | ~~Named contacts pulled from the 2026B CfP.~~ | **Resolved: use as-is for NOT, Milanković, Subaru, KMTNet, and VST/LBT.** SALT stays the exception — generic `salthelp@salt.ac.za` only, per item 14's original SALT-specific finding. |

## 6. Proposed YAML schema

One file per facility at `docs/contribution-types/_data/telescopes/<contribution-id>-<facility-slug>.yaml`:

`contribution_id` is normally a single string, but is list-valued for a record like GTC where more than one contribution ID funds the same single facility (as opposed to one ID spanning several facility records, per Section 4):

```yaml
contribution_id: KOR-KAS-S2       # groups sibling facility cards
facility: "Korean Microlensing Telescope"
aperture: "1.6m"
country: "Chile"
site: "Cerro Tololo"
latitude: -30.169                  # decimal degrees, for the map (Section 10); hemisphere is derived from this, not stored
longitude: -70.804
instrumentation: [Imaging]         # controlled vocabulary, drives the instrumentation filter
instrument_names: []               # optional, free-text named instruments for the card body, e.g. [OSIRIS+, EMIR, MEGARA, HiPERCAM] for GTC
wavelength_regime: [Optical]       # controlled vocabulary (Optical, NIR, UV, ...), same list as the datasets page, drives a filter
spectral_resolution_min: null      # R (resolving power), lowest mode offered; null for imaging-only facilities
spectral_resolution_max: null      # R, highest mode offered; equal to min for single-resolution instruments
multiplex: null                    # true | false | null — multi-object/fiber-fed capability vs. single-object, simple yes/no indicator
field_of_view: null                # free text with units, e.g. "1 deg x 1 deg" or "25.6' diameter" — informational, shown on the card
aeon: true                         # true | false | null (null = not yet confirmed) — badge shows only when true; KMTNet confirmed AEON-capable for all observations
too_capable: true                  # true | false | null — Target-of-Opportunity capability, badge shows only when true
observing_mode: queue              # service | queue | classical | mixed | null — mixed for facilities like Subaru where mode varies by instrument
contacts:                          # list, optional — the per-facility science contacts published in each cycle's NOIRLab CfP
  - name: "Min-Su Shin"
    email: "msshin@kasi.re.kr"
first_semester: "2026A"
time_available: "150 hours/semester"
duration: "5 years"
status: available                  # available | future_semester | tba
tac_process: default               # default (NOIRLab TAP) | special (e.g. GTC)
external_links:
  - label: "Korean Microlensing Telescope Network"
    url: "https://kmtnet.kasi.re.kr/kmtnet-eng/"
summary: >
  Roughly 150 hours per semester will be available on each of the telescopes
  of the Korean Microlensing Telescope Network...
```

`hemisphere` (Northern/Southern) is computed in the `conf.py` loader from the sign of `latitude` rather than hand-authored, so it can't drift out of sync with the map coordinates.

### 6.1 Discovery fields — capability-based, not science-based

Discovery is driven by facility *capabilities*, not by tagging facilities with the science cases they're nominally good for — UAT science-case tagging and Rubin-survey-affinity tagging were both considered and dropped as too broad to discriminate (nearly every facility could plausibly claim most UAT categories) and as scope creep beyond what a capability filter needs. Four capability fields were added instead:

- **`wavelength_regime`** — controlled vocabulary (Optical, NIR, UV, ...), same list the datasets page already uses. Drives a filter.
- **`spectral_resolution_min` / `spectral_resolution_max`** — the actual R (resolving power) value(s) an instrument offers, stored as numbers, not as a "low/medium/high" label. Different subdisciplines draw the low/medium/high line in very different places (e.g. R~1000 reads as "low" to an echelle-spectroscopy community and "medium" to a slitless-classification community), so the card and any filter show the real R number(s) rather than an adjective. If a filter bucket is useful for quick browsing, its label should state the numeric boundary explicitly (e.g. "R < 1,000" rather than "Low resolution") so nobody has to trust an assumed convention. Null for imaging-only facilities; instruments with multiple grism/grating modes get a min/max range rather than a single value.
- **`multiplex`** — simple `true`/`false`/`null` indicator for multi-object or fiber-fed capability (e.g. Subaru's PFS) versus single-object only. Deliberately kept as a yes/no flag rather than a fuller architecture taxonomy.
- **Clarification on `too_capable`:** every facility on this page requires a proposal to get time in the first place — `too_capable` isn't about ease of access, it's specifically whether the facility's *operations* support target-of-opportunity scheduling (interrupt or queue-based reactive observing) once a program has been awarded time, as distinct from fixed classical-mode scheduling.
- **`field_of_view`** — free-text with units (e.g. `"1 deg x 1 deg"`, `"25.6' diameter"`), shown on the card. FOV varies too much in shape/scale across imaging vs. IFU vs. slit spectroscopy to force into a single filterable unit, so it's informational rather than a filter for now.

Populating real numbers for `spectral_resolution_min/max` and `field_of_view` per facility is a migration-time data-collection task (pulling from each instrument's own documentation), same as the AEON/ToO gaps in Section 6.2 — not something to estimate or guess here.

### 6.2 What we already know per facility

Aperture and coarse instrumentation are already on the current page for all 15 facilities. The 2026B NOIRLab CfP's "Rubin in-kind contributions" section (Section 3.11), the GTC Announcement of Opportunity PDF, the original Trans-Pacific 2m proposal text, and a facility-by-facility review with Steve together closed out AEON/ToO status for all 14 facilities.

| Facility | Aperture | Instrumentation | AEON | ToO | Hemisphere (derived) |
|---|---|---|---|---|---|
| GTC 10.4m | 10.4m | Imaging and Spectroscopy — named: OSIRIS+, EMIR, MEGARA, HiPERCAM (per the official Announcement of Opportunity PDF) | **No** | **Yes** — general GTC operations support ToO, independent of the special in-kind allocation process | Northern |
| SALT 9.2m | 9.2m | Imaging and Spectroscopy | **No** | **Yes** | Southern |
| Subaru 8.4m | 8.4m | Imaging and Spectroscopy — named: HSC (wide-field imager, queue mode), PFS (multiplexed spectrograph, queue mode); all other common-use instruments in classical mode | **No** | **No** — Subaru operations may technically support ToO, but the Rubin community has better ToO access via Gemini North, so this contribution isn't positioned that way | Northern |
| LBT 2×8.4m | 8.4m ×2 | Imaging and Spectroscopy — named: LBC, MODS, LUCI (imaging/spectroscopy), PEPSI (spectroscopy); facility instruments only | **No** | **Yes** — INAF-executed within INAF blocks, urgent triggers need other-partner approval | Northern |
| VST 2.6m | 2.6m | Imaging — named: OmegaCAM | **No** | **Yes** — typically ~24h turnaround | Southern |
| NOT 2.56m | 2.56m | Spectroscopic classification of SNe — named: ALFOSC (low/medium-res) | **No** | **Yes** — specifically "Soft-ToO" (next-available-night, not an interrupt), afternoon-before trigger | Northern |
| Trans-Pacific 2m | 2m | Imaging (per the original proposal; still pre-first-light so no named instrument yet) | Planned — NCU intends to conform to AEON standards, but procedures aren't established yet (pre-first-light) | not documented — queue-mode observing is planned, but that wasn't framed as ToO specifically | Northern |
| Nishimura 1.8m (MOA) | 1.8m | Imaging | **Yes** | **Yes** | Southern |
| KMTNet ×3 | 1.6m | Imaging | **Yes** — available for all KMTNet observations, in two modes: 30 min at start/end of every night, or pre-allocated AEON nights | **Yes** | Southern (all 3 sites) |
| Milankovic 1.4m | 1.4m | Imaging | **Yes** | **Yes** — service mode, raw data in 24h, reduced in 72h | Northern |
| SAAO various | 1.9m–1.0m | Imaging and Spectroscopy | **Yes** | **Yes** | Southern |
| McLellan 1.0m | 1.0m | Imaging | **Yes** | **Yes** | Southern |
| RTT150/T100 | 1.5m/1.0m | Imaging | **Yes** | **Yes** — on predefined nights only, not full-time interrupt capability | Northern |

Additional operational detail worth carrying into the `summary`/notes text for the 7 facilities covered in the 2026B CfP (doesn't map cleanly to a single schema field, but is genuinely useful to a proposer):

- **Subaru:** proposals for the in-kind share must be submitted via the Gemini Phase-I Tool (PIT), not the standard NOIRLab dashboard — worth calling out since it's an easy step to miss.
- **VST & LBT:** both are strictly service-mode, executed by INAF staff — "programs requiring a strictly fixed cadence cannot be supported." VST data lands in the ESO Science Archive (1yr proprietary); LBT raw/calibration data at `archive.lbto.org` (1yr proprietary), with reduction pipelines varying by instrument (INAF–OARoma for LBC/MODS/LUCI imaging, AIP for PEPSI, SIPGI for LUCI/MODS spectroscopy).
- **KMTNet:** AEON access mechanics (and an API) are documented at `kmtnet.kasi.re.kr/aeon`.
- **NOT:** SN classification spectra are uploaded to WISeREP/TNS within 48h with no proprietary period at all (immediately public).
- **SALT:** contact is the generic `salthelp@salt.ac.za` only — deliberately not listing individual names (e.g. the CfP's listed contacts are stale; at least one has since left SALT).
- **Confirmed named contacts (2026B CfP), everyone else:** NOT — Jesper Sollerman, `jesper@astro.su.se`. Milanković — Maša Lakićević, `mlakicevic@aob.rs`. Subaru — Yusei Koyama, `koyama@naoj.org`, and Yousuke Utsumi, `yousuke.utsumi@nao.ac.jp`. KMTNet — Min-Su Shin, `msshin@kasi.re.kr`. VST and LBT (shared) — Felice Cusano, `felice.cusano@inaf.it`, plus general mailboxes `vst@inaf.it` and `lbt-italia@inaf.it` respectively.
- **Trans-Pacific 2m:** per the original proposal, NCU is providing ~40 nights/year for 10 years, queue-mode (no travel required), raw data within 24h and fully reduced/calibrated data within 48h, with photometric catalogs on request and a helpdesk currently under development. `aeon` is left `null` rather than `true` since AEON conformance is stated as an intention pending commissioning, not yet operational — the nuance ("planned, pending first light") belongs in the record's free-text `summary` rather than forcing the boolean.

One oddity: both the NOT and Milankovic sections of the 2026B CfP text give an observation window in the past ("June through October 2025" / "July through December 2025") — likely unrevised boilerplate carried over from an earlier semester's call rather than a real 2026B window. Not something we control, but worth flagging back to whoever maintains that CfP text.

**All 15 facilities now have confirmed AEON/ToO status.** The only fields still genuinely open are: `contacts` (blank for Trans-Pacific 2m, Nishimura, McLellan, SAAO various, and RTT150/T100 — "no contact yet" per your answers), and `instrument_names`/`spectral_resolution_min/max`/`field_of_view`, which weren't part of this AEON/ToO/contact sweep and remain a separate data-collection pass against each instrument's own documentation.

Facility-specific fields (`facility`, `aperture`, `country`, `site`, `instrumentation`) live on every record. Fields that are naturally authored once per contribution (`summary`, `time_available`, `duration`, `status`, `tac_process`) are also present on every sibling record but expected to match — the `conf.py` loader will warn (at minimum) if sibling records under the same `contribution_id` disagree on these fields, so drift gets caught at build time rather than silently rendering inconsistent cards.

## 7. Migration inventory

All 15 current table rows, mapped to planned records. Contribution IDs marked with `*` are the multi-facility groups from Section 4.

| Facility | Location | Contribution ID |
|---|---|---|
| Gran Canary Telescope (GTC) 10.4m | La Palma, Spain | ESP-BCM-S5 + ESP-IAC-S1 (single card, list-valued ID) |
| South African Large Telescope (SALT) 9.2m | SAAO, South Africa | SZA-SAA-S1 |
| Subaru Telescope 8.4m | Maunakea, USA | JAP-JPG-S1 |
| Large Binocular Telescope 2×8.4m | Mt. Graham, USA | ITA-INA-S18 * |
| VLT Survey Telescope 2.6m | Cerro Paranal, Chile | ITA-INA-S18 * |
| Nordic Optical Telescope 2.56m | La Palma, Spain | SWE-STK-S3 |
| Trans-Pacific Two-Meter Telescope 2m | San Pedro Martir, Mexico | TAI-NCU-S1 |
| Nishimura 1.8m | Mt John Observatory, New Zealand | NZL-AUK-S1 * |
| Korean Microlensing Telescope 1.6m | Cerro Tololo, Chile | KOR-KAS-S2 * |
| Korean Microlensing Telescope 1.6m | Siding Springs Observatory, Australia | KOR-KAS-S2 * |
| Korean Microlensing Telescope 1.6m | SAAO, South Africa | KOR-KAS-S2 * |
| Milankovic Telescope 1.4m | Astronomical Station Vidojevica, Serbia | SER-SAG-S2 |
| Various SAAO telescopes 1.9m–1.0m | SAAO, South Africa | SZA-SAA-S4 |
| McLellan 1.0m | Mt John Observatory, New Zealand | NZL-AUK-S1 * |
| RTT150 1.5m & T100 1.0m | TÜBITAK National Observatory, Türkiye | TUR-AKD-S1 |

GTC is a single facility record with a list-valued `contribution_id` (`[ESP-BCM-S5, ESP-IAC-S1]`) — resolved in Section 4, no separate decision needed during implementation.

### 7.1 Facility links

`external_links` (already in the schema, Section 6) will carry each facility's official page(s). The current `in-kind-program.lsst.io` page has no facility links at all in its table and only a handful in its prose. Its predecessor, `lsst.org/scientists/in-kind-program/telescope-resources` (still live, last modified March 2025), turns out to have official links for every one of the 14 facilities, including two facilities the current site is missing links for entirely (Trans-Pacific 2m, RTT150/T100). Compiled inventory, ready to carry into the YAML records:

| Facility | Link(s) |
|---|---|
| GTC 10.4m | [Home](https://www.gtc.iac.es/GTChome.php), [Instrumentation](https://www.gtc.iac.es/instruments/instrumentation.php) |
| SALT 9.2m | [Home](https://astronomers.salt.ac.za/), [Instrumentation](https://astronomers.salt.ac.za/instruments/), [Call document](https://astronomers.salt.ac.za/proposals/), [Simulation tools](https://astronomers.salt.ac.za/software/) |
| Subaru 8.4m | [Observing info](https://subarutelescope.org/en/for_researchers/observation/index.html), [Instrumentation](https://subarutelescope.org/Observing/Instruments/index.html) |
| LBT 2×8.4m | [Home](https://www.lbto.org/), [Instruments](https://scienceops.lbto.org/instruments/), [Data archive](http://archive.lbto.org), [SIPGI reduction pipeline](https://pandora.lambrate.inaf.it/sipgi/) |
| VST 2.6m | [Home (INAF, more specific than the ESO facility page)](https://vst.inaf.it/home), [OmegaCAM instrument page](https://www.eso.org/sci/facilities/paranal/instruments/omegacam.html), [Astro-WISE reduction environment](https://www.astro-wise.org/portal/), [Data-reduction training sessions](https://vst.inaf.it/user-support/learning-sessions-for-data-reduction) |
| NOT 2.56m | [Instrumentation](https://www.not.iac.es/instruments/), [WISeREP/TNS](https://www.wiserep.org/) |
| Trans-Pacific 2m | [Home](https://www.astro.ncu.edu.tw/ncutwom/) *(missing from the current site entirely)* |
| Nishimura 1.8m / McLellan 1.0m | [Mt John Observatory wiki](https://wiki.canterbury.ac.nz/pages/viewpage.action?pageId=152307302) |
| KMTNet ×3 | [Network home](https://kmtnet.kasi.re.kr/kmtnet-eng/), [AEON access info](https://kmtnet.kasi.re.kr/aeon) |
| Milankovic 1.4m | [Telescope page](https://vidojevica.aob.rs/index.php?option=com_content&view=article&id=40&Itemid=249), [Station page](https://vidojevica.aob.rs/index.php?option=com_content&view=article&id=8&Itemid=35), [Andor iKon-L 936 CCD](https://vidojevica.aob.rs/index.php?option=com_content&view=article&id=21&Itemid=28) |
| SAAO various | [1.0m](https://www.saao.ac.za/astronomers/1-0m/), [1.9m](https://www.saao.ac.za/astronomers/1-9m/) |
| RTT150 / T100 | [T100](https://tug.tubitak.gov.tr/en/teleskoplar/t100-telescope), [RTT150](https://tug.tubitak.gov.tr/en/teleskoplar/rtt150-telescope-0) *(missing from the current site entirely)* |

Note: VST's most authoritative link is actually `vst.inaf.it/home` (INAF's own facility page), not the general ESO Paranal facilities page I'd originally proposed — replaced above.

Two things worth flagging while comparing the two sources:

- ~~Mt John link discrepancy.~~ **Resolved: use `wiki.canterbury.ac.nz/pages/viewpage.action?pageId=152307302`** (the older `lsst.org` link) — it redirects correctly. The current site's `ucdigitalsms.atlassian.net` link is dead; the university's wiki appears to have moved to Atlassian-hosted pages under the `canterbury.ac.nz` hostname, and that's the one that actually resolves.
- ~~First Semester discrepancy.~~ **Resolved: the current `in-kind-program.lsst.io` dates are accurate.** `lsst.org` is no longer maintained — its `2026A` values for LBT, VST, Mt John's two telescopes, SAAO various, and RTT150/T100 are stale, not evidence of a migration regression. Use the current site's `TBA`/dated values as ground truth.

**Note on the NOIRLab Call for Proposals as a link/data source:** the standard CfP document at `noirlab.edu/science/observing-noirlab/proposals/call-for-proposals` gets a per-semester section on Rubin in-kind facilities (e.g. a "Rubin In-Kind Facilities" section starting with the 2026B cycle), alongside a companion announcement Steve posts to `community.lsst.org` each cycle (e.g. the [2026B announcement](https://community.lsst.org/t/2026b-noirlab-call-for-proposals-rubin-in-kind-facilities-webinars/11742), which listed Subaru, NOT, VST, LBT, SALT, KMTNet, and Milanković as offering time that semester, plus facility webinar links). This is a real, recurring source worth checking each cycle for facility-specific updates — and it's also a natural model for the "general CfP" opportunity entries in Section 9. One caveat: my web-fetch tool kept returning a stale, out-of-date (2024B) snapshot of the CfP page itself across repeated attempts in this session, despite search results and the community post confirming the live page currently covers 2026B — worth pulling that page by hand rather than relying on my fetch of it.

## 8. Out of scope

- No change to `general-pool.rst`, `contributed-resources.rst`, or any page outside Contributed Telescope Access.
- No new intake/CSV-pull pipeline for telescope facility data (see Section 3).
- No change to the datasets page itself, beyond possibly factoring out shared CSS/JS if useful.

## 9. Featured opportunities section (new — no equivalent on the datasets page)

A callout section at the very top of the page, above the filter bar, surfacing time-sensitive items the coordinator wants visibility on — e.g. the live [GTC observing time opportunity](https://community.lsst.org/t/gtc-observing-time-opportunity-for-the-us-and-chilean-community/12233) (LoI due Aug 7 2026, GTC CfP opens Sept 1 2026, Spanish TAC deadline Oct 1 2026) and a reminder that the standard NOIRLab Call for Proposals for 2027A is expected to open around September 1, 2026.

Two kinds of entries, both content-managed rather than derived from the facility records:

- **Special call** — a one-off process outside the normal NOIRLab TAP (GTC is the current example): title, summary, an ordered milestone list with dates, links (announcement post, submission portal), and the `contribution_id`(s) it relates to (so it can cross-link to the matching facility card(s) below).
- **General CfP reminder** — a recurring nudge about the standard NOIRLab TAP cycle, which is the umbrella process for most of the facilities on this page: title, summary, one or more milestone dates (can be marked `approximate: true`, e.g. "expected ~Sept 1"), and a link to the NOIRLab proposals page.

Proposed data source: `docs/contribution-types/_data/opportunities/<id>.yaml`, loaded the same way as facility records, e.g.:

```yaml
id: gtc-2026b-special-call
title: "GTC Observing Time Opportunity for the US and Chilean Community"
kind: special_call                 # special_call | general_cfp
related_contribution_ids: [ESP-BCM-S5, ESP-IAC-S1]
summary: >
  A special allocation of ~2 nights/semester on the 10.4m Gran Telescopio
  Canarias (GTC) is available to the US and Chilean community via a
  Letter-of-Intent + Spanish TAC co-PI process. LoIs are capped at 3x the
  available allocation; Cosmology proposals are typically paired with the
  Barcelona-Madrid LSST groups, all other disciplines with the IAC,
  though pairing depends on demand and staff availability.
milestones:
  - label: "Letters of Intent due"
    date: 2026-08-07
  - label: "Matchmaking & feasibility notifications"
    date: 2026-08-31
    approximate: true
  - label: "GTC Call for Proposals opens"
    date: 2026-09-01
  - label: "Spanish TAC submission deadline"
    date: 2026-10-01
links:
  - label: "Full announcement"
    url: "https://community.lsst.org/t/gtc-observing-time-opportunity-for-the-us-and-chilean-community/12233"
  - label: "LoI submission portal"
    url: "https://lsst.ice.csic.es/"
  - label: "Official Announcement of Opportunity (PDF)"
    url: "https://community.lsst.org/uploads/short-url/d2UEv88IgQXxlDY42eGCG0visIK.pdf"
contact:
  name: "Steven Margheim"
  email: "steven.margheim@noirlab.edu"
  note: "eligibility, general process, program opportunities — technical instrument questions go to the GTC website or submission-portal contacts instead"
visible_until: 2026-10-01           # drops from the featured section automatically after this date
```

Visibility (`visible_until`) is computed at build time against the build date (same pattern the datasets loader already uses for `last_updated`, just compared forward instead of derived from git history). Opportunities change on a months-long cadence, so relying on the existing on-push build — triggered whenever the coordinator adds, edits, or removes an opportunity record — is sufficient; no scheduled rebuild needed (open item 6, resolved).

Rendering: a row of highlighted cards (visually distinct from the facility cards below — e.g. an accent border/background) sorted by nearest upcoming milestone, each showing its milestone list and links. When `related_contribution_ids` is set, the card links down to the matching facility card(s).

## 10. Facility map (new — no equivalent on the datasets page)

A world map showing all facility locations, for at-a-glance geographic browsing (useful given the program spans both hemispheres and a wide longitude range).

- Extend the facility schema (Section 6) with `latitude`/`longitude` (decimal degrees).
- **Resolved (Section 5, item 5): a single inline static SVG world outline** in `_static/`, with one marker per facility positioned at build time via a simple equirectangular projection (`x = (lon+180)/360 * width`, `y = (90-lat)/180 * height`) computed in the `conf.py` loader and passed into the Jinja template — no external map tile service, no new JS dependency, consistent with the rest of the site. Clicking a marker scrolls to and highlights the matching card, reusing the scroll/highlight interaction already built for the datasets page's table-row-to-card links. Markers filter live using the same `filter_tokens` mechanism as the cards/table.
- Facilities that share a site (e.g. the SAAO cluster, Mt John's two telescopes) will have overlapping or near-identical coordinates — markers get simple positional offsetting rather than real zoom-to-separate; precise on-mountain location isn't useful for discovery, rough lat/long is enough to judge feasibility (hemisphere, region).
- Leaflet.js + OpenStreetMap tiles was considered and rejected — real pan/zoom isn't needed since exact location doesn't add discovery value, and it would add an external tile-request dependency this site doesn't otherwise have.
- Need a source for the world outline itself (e.g. a simplified Natural Earth land-boundary path converted to SVG) — this is an implementation-time task, not a data question.

## 11. Next step

Once items in Section 5 are answered, I'll write a staged implementation plan (data migration → `conf.py` loader → template → local build/test via your `rubin-docs` conda env → PR) and start on it.
