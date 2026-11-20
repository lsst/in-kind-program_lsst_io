# Test fixtures

`docs/contribution-types/_data/` and `docs/_static/world-outline.svg` here mirror the layout
of the real site, so the loaders' path logic works unchanged. All values are invented
(no real people, institutions' contacts or emails).

Use them two ways:

* in tests, `build_contexts(FIXTURE_DATA_DIR, today=datetime.date(2027, 3, 15))`;
* for a local preview build, see the "Local preview switches" section of the root README.

## The fixed date: 2027-03-15

On that date the five opportunity records in `opportunities/` are in these phases:

| File | Phase on 2027-03-15 | Why |
|---|---|---|
| `fixture-upcoming-call.yaml` | upcoming | `opens` is 2027-04-01 |
| `fixture-open-call.yaml` | open | opened 2027-03-01, last deadline 2027-04-15 |
| `fixture-in-review-call.yaml` | in review | deadline 2027-03-01 passed, results due 2027-04-01 |
| `fixture-closed-call.yaml` | closed | results announced 2027-02-15 |
| `fixture-hidden-call.yaml` | hidden | `visible_until` was 2027-03-01 |

`datasets/TST-FIX-S2.yaml` carries a `curated.highlight` that runs until 2027-04-30.

If you change a date here, update the table and `tests/test_fixture_data.py`.
The golden snapshot of these banners is `tests/snapshots/fixture_opportunities.json`, checked by
`tests/test_opportunity_loader.py`. After an intended change, regenerate it with
`tox run -e test -- --update-snapshots` and review the diff.
