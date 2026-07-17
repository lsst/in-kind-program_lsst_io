# Contributed Telescope Access page redesign — implementation plan

Companion to `telescope-page-redesign-requirements.md`. Six stages, each a separate, independently reviewable commit or PR against `lsst/in-kind-program_lsst_io`, so nothing has to land as one large diff.

## Stage 0 — Environment check

Before writing anything: confirm the `rubin-docs` conda env (Python 3.12) has `documenteer[guide]>=2.0,<3.0` installed per `requirements.txt`, and that `tox run -e html` builds the current `main` branch cleanly as a baseline. This also confirms `sphinx-design` and `sphinx-jinja` are available — both are bundled by `documenteer[guide]` and already used by the datasets page, so no new dependencies are expected for the facility cards/filter bar/table. The map (Stage 4) and opportunities banner (Stage 3) are also dependency-free (static SVG, no JS libraries beyond the vanilla JS already in the codebase), so `requirements.txt` shouldn't need to change at all this project.

## Stage 1 — Data migration (no visible page change)

Add one YAML file per facility at `docs/contribution-types/_data/telescopes/<contribution-id>-<facility-slug>.yaml`, per the Section 6 schema, plus two opportunity records at `docs/contribution-types/_data/opportunities/`. This stage only adds data files — the live page still renders the old static content until Stage 3, so it's safe to merge early and let Steve review/correct the actual data in a plain YAML diff before any page logic exists.

Facility records (15 files, mapping from Section 7's migration inventory):

- All confirmed AEON/ToO/instrument/contact/link data from the requirements doc goes in directly.
- Two content fixes happen here, not as a follow-up: the Milanković record uses `SER-SAG-S2` (the table ID, not the prose's `SER-SAG-S1` typo), and the duplicated "Telescope 1.4m Telescope 1.4m" text in the facility name is cleaned up to "Milanković Telescope 1.4m".
- GTC gets a single record with `contribution_id: [ESP-BCM-S5, ESP-IAC-S1]`.
- KMTNet's three site records and Mt John's two telescope records share a `contribution_id` for the sibling cross-link (Stage 3).
- Fields with no data yet (`instrument_names`, `spectral_resolution_min/max`, `field_of_view`, and `contacts` for Trans-Pacific 2m, Nishimura, McLellan, SAAO various, RTT150/T100) are left `null`/empty rather than guessed.

Opportunity records (2 files): the GTC special call (with the milestone table, links, and contact from the AO PDF) and a 2027A general-CfP reminder (`~Sept 1, 2026` milestone marked `approximate: true`).

**Verification:** `python -c "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in pathlib.Path('docs/contribution-types/_data').rglob('*.yaml')]"` to confirm every file parses. No Sphinx build needed yet.

## Stage 2 — `conf.py` loaders

Add `_load_contributed_telescopes()` and `_load_contributed_opportunities()` to `conf.py`, following the shape of the existing `_load_contributed_datasets()`:

- Read every facility YAML, normalize strings (reuse `_normalize_strings`), compute a slug per record.
- Derive `hemisphere` from `latitude`'s sign.
- Derive map marker `x`/`y` via the equirectangular projection from Section 10, with a small deterministic offset applied to records sharing near-identical coordinates (SAAO cluster, Mt John) so markers don't fully overlap.
- Group records by `contribution_id` (handling the list-valued GTC case) to build each record's `siblings` list for the "Also available under this contribution" cross-link.
- Build `filter_tokens` covering the confirmed filter facets: instrumentation, wavelength regime, spectral-resolution bin (bucketed from `spectral_resolution_min/max` at load time, with the bucket label carrying the real R numbers per Section 6.1), multiplex, status, hemisphere, and aperture band (parsed from the `aperture` string).
- Build `search_text` the same way the datasets loader does (title/facility, summary, instrumentation, contacts).
- Add a **consistency check**: for records sharing a `contribution_id`, warn (via `logger.warning` in the Sphinx build log — not a hard failure) if `summary`, `time_available`, `duration`, `status`, or `tac_process` disagree, per the note in Section 6.2. This catches sibling-record drift at build time instead of silently rendering mismatched cards.
- `_load_contributed_opportunities()` computes each record's live/expired state from `visible_until` vs. the build date, and sorts by nearest upcoming milestone.
- Expose both via `jinja_contexts["contributed_telescopes"]` and `jinja_contexts["contributed_opportunities"]`.

**Verification:** a throwaway `python -c "from conf import _load_contributed_telescopes; import json; print(json.dumps(_load_contributed_telescopes(), indent=2, default=str))"` (run from the repo root) to eyeball the loader output — filter tokens, siblings, hemisphere, marker coordinates — before wiring it into any template.

## Stage 3 — `contributed-telescope.rst` rewrite

Replace the current static grid table + prose sections with a `.. jinja:: contributed_telescopes` block mirroring the datasets page's structure:

- **Opportunities banner** at the very top, above the filter bar: a row of accent-styled cards from `contributed_opportunities`, each showing its milestone list and links, cross-linking to matching facility cards via `related_contribution_ids`.
- **Filter bar**: seven controls (instrumentation, wavelength regime, spectral resolution bin, multiplex, status, hemisphere, aperture band) plus the free-text search box, following the same `<select>` + vanilla-JS `applyFilters()` pattern already in `contributed-datasets.rst`.
- **Sortable summary table**, same column-click-to-sort behavior as the datasets page.
- **World map** (Stage 4, but the `<svg>` container and marker loop live here).
- **Card grid**: one `.. grid-item-card::` per facility, `:class-item:` carrying `filter_tokens` for filtering. Card body: aperture, location, instrumentation badges, wavelength/resolution/multiplex/FOV when known, AEON/ToO badges (shown only when `true`, per the resolved default), contacts, external links, and the sibling cross-link list when `siblings` is non-empty.

**Verification:** `tox run -e html`, then open `_build/html/contribution-types/contributed-telescope.html` locally and manually exercise every filter, the search box, the status toggle, column sorting, and the sibling cross-links (KMTNet's 3, Mt John's 2, VST/LBT's 2).

## Stage 4 — World map

- Source a simplified, permissively-licensed world land-boundary outline (e.g. a low-resolution Natural Earth 110m coastline export converted to a single SVG `<path>`) and commit it as a static asset under `docs/_static/`. This is a one-time asset-sourcing task, not a build-time dependency — confirm license terms allow redistribution before committing it.
- Render facility markers as `<circle>` elements positioned from the `x`/`y` computed in Stage 2, each carrying the same `filter_tokens` as its card so the existing filter JS hides/shows markers identically to cards and table rows.
- Click handler scrolls to and highlights the corresponding card (reusing the datasets page's `ikc-highlight` pattern).

**Verification:** visually confirm marker placement against a few known coordinates (e.g. La Palma facilities should cluster near each other; Chile/Australia/South Africa KMTNet markers should be visibly separated), and confirm clicking each marker scrolls to the right card.

## Stage 5 — Full QA pass

- `tox run -e lint` (pre-commit: trailing whitespace, YAML/JSON/TOML validity, `blacken-docs` on `conf.py`).
- `tox run -e linkcheck` — expect the two pre-existing `linkcheck_ignore` entries (SALT, Vidojevica) to still apply; check whether the newly added links (INAF, TÜBITAK, NCU, etc.) need similar allowances if they block on bot detection.
- Manual pass on mobile viewport width, since the current table is explicitly called out as hard to scan on mobile (Section 1's motivation).
- Confirm the sibling-record consistency warning (Stage 2) fires correctly by temporarily mismatching a test value, then remove the test change.
- Re-check the two content fixes from Stage 1 actually landed (Milanković ID and name).

## Stage 6 — PR and rollout

Open the PR(s) against `lsst/in-kind-program_lsst_io` (Stages 1–2 can be one PR since they're both invisible on the live site; Stages 3–5 as a second PR once the first is merged, or all together if you'd rather review it as one unit — your call once you see how Stage 1's data diff reads). After merge, the CI build deploys automatically per the existing on-push workflow (no new scheduled rebuild needed, per Section 5 item 6).

**Not in this rollout, tracked as follow-up:** filling in `contacts` for Trans-Pacific 2m, Nishimura, McLellan, SAAO various, and RTT150/T100, and `instrument_names`/`spectral_resolution_min/max`/`field_of_view` across most facilities (Section 6.2's closing note) — none of this blocks shipping the redesigned page structure, since every field renders gracefully when null/empty.
