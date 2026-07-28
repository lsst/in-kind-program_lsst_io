# Syncing contributions from the CSVs — cheatsheet

Quick reference for running `sync_contributions.py` and getting the result onto the live site. For the full design rationale, see `revamp-planning/04-implementation-plan.md`.

## 1. Export the two CSVs

You need two files, both exported fresh right before you run the script:

1. **Form responses** — open the "In-kind Contribution Resources" response spreadsheet (Google Sheets, linked from the form's Responses tab) → File → Download → Comma Separated Values (.csv).
2. **Contributions/proposal spreadsheet** — same idea, export the proposal-tracking spreadsheet (the one with Country/Institute/ID/Category/Recipient Group columns) to CSV.

Save them somewhere handy, e.g. `~/Downloads/form_responses.csv` and `~/Downloads/contributions.csv`.

> If the form has changed since the script was written, it'll fail fast with a clear error ("form CSV has N columns, expected 37") rather than silently misreading columns — see Troubleshooting below.

## 2. Run the script

```
cd /Users/smargheim/Project/IKdataset_docs
python3 scripts/sync_contributions.py \
  --contributions ~/Downloads/contributions.csv \
  --form-responses ~/Downloads/form_responses.csv
```

Needs `pyyaml` installed (`pip install pyyaml` if you don't already have it — it's likely already present since `conf.py` uses it too).

**First time running it / a big backlog of known changes?** Add `--yes` to apply everything without stopping to ask:
```
python3 scripts/sync_contributions.py --contributions ~/Downloads/contributions.csv --form-responses ~/Downloads/form_responses.csv --yes
```

## 3. Answer the review prompts

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

## 4. Read the summary

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

Anything flagged `NEEDS-REVIEW` needs a manual look before it ships — see step 5.

## 5. Review the flagged files

```
git status
git diff -- docs/contribution-types/_data/
```

For every **new** record (`needs_review: true` in its `curated:` block), open the YAML and check/fill in:
- `title` / `country` / `institute` — auto-filled from the spreadsheet if the ID was found there; if not, `title` falls back to whatever the submitter typed as their deliverable name, and `country`/`institute` are `null` and need a manual fill-in.
- `curated.primary_recipient` (datasets) — who the in-kind team is assigning this to, if not already picked up from the spreadsheet.
- `curated.summary` (datasets) — seeded from the submitter's own summary text; fix spelling/tone, or rewrite for a public audience.
- `curated.wavelength_regime` (datasets) — the form doesn't capture this at all; fill in manually.

Once you're happy, remove the `needs_review: true` line (or leave it if you want to circle back later — it's not read by the page, it's just a flag for you).

For **updated** existing records, a normal `git diff` review is enough — `curated` is never touched by the script, so you're only reviewing factual `form_data` changes.

## 6. Build and preview locally

```
conda activate rubin-docs
tox run -e html
open _build/html/contribution-types/contributed-datasets.html
open _build/html/contribution-types/contributed-software.html
```

Check the new/updated cards render as expected — filters, badges, and the summary table pick up new records automatically, nothing else to wire up.

## 7. Commit, push, open a PR

```
git checkout -b sync-<short-date-or-topic>
git add docs/contribution-types/_data/
git commit -m "Sync contributions from <date> form/spreadsheet export"
git push -u origin sync-<short-date-or-topic>
```

Then open the PR the same way as always (GitHub prints the link after the push, or visit `https://github.com/lsst/in-kind-program_lsst_io/compare/main...sync-<branch>`).

## Troubleshooting

- **`form CSV has N columns, expected 37`** — the form's questions changed (added/removed/reordered). Open `scripts/sync_contributions.py`, find `FORM_COLUMNS` near the top, and update it to match the new column order before re-running. Column *position* matters more than the header text here, since the form asks "Maintenance Plan & Updates" twice (software vs. dataset sections) and the script tells them apart by position, not name.
- **`unexpected header row`** on the `--contributions` CSV — the proposal spreadsheet's layout changed. Check that row 3 (index 2) still has `ID` in column C; if the sheet's structure shifted, `load_contributions()` needs its column indices updated.
- **A software card got created for something that's actually a dataset (or vice versa)** — the script only treats spreadsheet category codes `4.2`/`4.3` as software; anything else (including a Datasets category) is left for the direct-response Datasets path. If this happens, check the `Category` column for that row in the spreadsheet.
- **Script created a placeholder-looking dataset card with no data** — this shouldn't happen; unlike software, a Datasets card is only ever created when there's an actual form response for that ID. If you see one, check `curated.needs_review` and the `form_data` — it likely came from a real (possibly incomplete) submission.
- **Want to redo a run** — the script is safe to re-run; anything you declined or that's unchanged is simply left alone next time too.
