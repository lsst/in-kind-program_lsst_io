# Syncing contributions from the CSVs — cheatsheet

Quick reference for running `sync_contributions.py` and getting the result onto the live site. For the full design rationale, see `revamp-planning/04-implementation-plan.md`.

Examples below assume you're in your local clone of `in-kind-program_lsst_io` (wherever you keep it) and use a generic `<repo>` placeholder for that path.

## 1. Update your local clone

Other people run this same script, so someone else's sync may already be on `main`. Pull first so the review-diff in step 3 compares against the real current state and you don't open a PR that conflicts with one already merged:

```
cd <repo>
git checkout main
git pull
```

## 2. Export the form responses CSV

Open the "In-kind Contribution Resources" response spreadsheet (Google Sheets, linked from the form's Responses tab) → File → Download → Comma Separated Values (.csv). Save it somewhere handy, e.g. `~/Downloads/form_responses.csv`.

That's the only CSV you need for ongoing syncs. The proposal/contributions spreadsheet (`--contributions`) was a one-off used to bulk-populate the initial set of software cards and isn't something you re-export going forward — see step 2a if you think you need it anyway.

> If the form has changed since the script was written, it'll fail fast with a clear error ("form CSV has N columns, expected 37") rather than silently misreading columns — see Troubleshooting below.

### 2a. New contributions: pending cards are now hand-created, not auto-generated

Without the `--contributions` spreadsheet feeding it, the script only creates a card once a contribution's closing form response actually arrives — there's no more automatic "pending" placeholder for something merely proposed. If you want a contribution to show up as pending *before* its form is submitted, create a bare-bones YAML file for it yourself first:

```yaml
contribution_id: NEW-ID-S1
title: Working title
country: Country
institute: Institute
form_data:
  submitted: false
curated:
  status_override: null
```
(add whichever other blank fields the schema expects — copy the shape from a neighboring file in `_data/software/` or `_data/datasets/`). Once that file exists, a future sync run will fill in `form_data` from their response the normal way, going through the review-diff prompt like any other update.

## 3. Run the script

```
cd <repo>
python3 scripts/sync_contributions.py --form-responses ~/Downloads/form_responses.csv
```

Needs `pyyaml` installed (`pip install pyyaml` if you don't already have it — it's likely already present since `conf.py` uses it too).

**Got a backlog of several changes you already know you want?** Add `--yes` to apply everything without stopping to ask:
```
python3 scripts/sync_contributions.py --form-responses ~/Downloads/form_responses.csv --yes
```

## 4. Answer the review prompts

For every *existing* card the CSVs would change, you'll see a before/after diff and a prompt:

```
--- update available: NZL-AUK-S2 -- The MOA Archive... ---
  data_volume:
    was: (empty)
    now: 50TB, 10 billion epochs
  ...
Apply this update? [y]es / [n]o (default) / [a]ll remaining / [q]uit remaining:
```

| Answer | What it does |
|---|---|
| `y` | Apply this one change, keep asking about the rest |
| `n` / Enter | Skip this one, leave that file untouched, keep asking about the rest |
| `a` | Apply this and every remaining change without asking again |
| `q` | Stop asking — skip this and every remaining change (files already written this run stay written) |

Brand-new cards (no existing file) are never prompted — they're always created, and marked `needs_review: true` inside the YAML so you don't lose track of them.

## 5. Read the summary

At the end you get a report like:

```
=== Software ===
2 new, 1 updated, 1 skipped (declined), 0 unchanged
  new: SER-SAG-S1, TEST-NEW-S1
  NEEDS-REVIEW: drafted 2 companion dataset record(s): SER-SAG-S1, TEST-NEW-S1

=== Datasets ===
2 new, 1 updated, 1 skipped (declined), 0 unchanged
  NEEDS-REVIEW (new): TEST-NEW-D1, TEST-NEW-D2
```

Anything flagged `NEEDS-REVIEW` needs a manual look before it ships — see step 6.

## 6. Review the flagged files

```
git status
git diff -- docs/contribution-types/_data/
```

For every **new** record (`needs_review: true` in its `curated:` block) that wasn't hand-created ahead of time (step 2a), open the YAML and check/fill in:
- `title` / `country` / `institute` — `title` falls back to whatever the submitter typed as their deliverable name; `country`/`institute` are `null` since the form doesn't ask for them, and need a manual fill-in.
- `curated.primary_recipient` (datasets) / `form_data.primary_recipient_group` (software) — who the in-kind team is assigning this to.
- `curated.summary` (datasets) — seeded from the submitter's own summary text; fix spelling/tone, or rewrite for a public audience.
- `curated.wavelength_regime` (datasets) — the form doesn't capture this at all; fill in manually.
- `form_data.category` / `activity_description` / `timeline` (software) — not captured by the form at all; fill in manually if relevant.

Once you're happy, remove the `needs_review: true` line (or leave it if you want to circle back later — it's not read by the page, it's just a flag for you).

For **updated** existing records, a normal `git diff` review is enough — `curated` is never touched by the script, so you're only reviewing factual `form_data` changes.

## 7. Build and preview locally

```
# activate however you manage this project's Python env, e.g.:
conda activate rubin-docs
tox run -e html
open _build/html/contribution-types/contributed-datasets.html
open _build/html/contribution-types/contributed-software.html
```

Check the new/updated cards render as expected — filters, badges, and the summary table pick up new records automatically, nothing else to wire up.

## 8. Commit, push, open a PR

If a while has passed since step 1, `git pull` on `main` once more before branching — someone else may have merged in the meantime.

```
git checkout -b sync-<short-date-or-topic>
git add docs/contribution-types/_data/
git commit -m "Sync contributions from <date> form/spreadsheet export"
git push -u origin sync-<short-date-or-topic>
```

Then open the PR the same way as always (GitHub prints the link after the push, or visit `https://github.com/lsst/in-kind-program_lsst_io/compare/main...sync-<branch>`).

## Troubleshooting

- **`form CSV has N columns, expected 37`** — the form's questions changed (added/removed/reordered). Open `scripts/sync_contributions.py`, find `FORM_COLUMNS` near the top, and update it to match the new column order before re-running. Column *position* matters more than the header text here, since the form asks "Maintenance Plan & Updates" twice (software vs. dataset sections) and the script tells them apart by position, not name.
- **Script wants to blank out `category`/`primary_recipient_group`/`activity_description`/`timeline` on an existing software card** — those four fields only ever come from the (now-retired) `--contributions` spreadsheet, so if you *do* pass `--contributions` and a contribution's row is missing from that export, the script has nothing to source them from. Decline (`n`) that part of the review, or just don't pass `--contributions` at all for a normal sync — without it, those fields are always preserved as-is rather than cleared.
- **Script created a placeholder-looking card with no data** — shouldn't happen from a normal sync; a card is only ever created when there's an actual form response for that ID (or you hand-created one per step 2a). If you see one, check `curated.needs_review` and the `form_data` — it likely came from a real (possibly incomplete) submission.
- **Want to redo a run** — the script is safe to re-run; anything you declined or that's unchanged is simply left alone next time too.
- **You do need to re-run the retired `--contributions` bulk path** (e.g. a large batch of brand-new proposed contributions needs pending placeholders again) — it's still supported, just optional now: `python3 scripts/sync_contributions.py --contributions ~/Downloads/contributions.csv --form-responses ~/Downloads/form_responses.csv`. Same category-code caveat as before: only `4.2`/`4.3` rows become software placeholders; anything else is left for the direct Datasets-response path.
