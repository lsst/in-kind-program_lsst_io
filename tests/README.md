# Tests

All tests run through one entry point:

    tox run -e test

The suite has five parts:

* **Snapshot tests** (`test_conf_snapshots.py`): golden-file tests for the
  card loaders in `ikp_data/loaders/`. See below.
* **Schema, check and validator tests** (`test_schemas.py`): the pydantic
  models in `ikp_data/schemas.py`, the cross-record checks, and the
  `python -m ikp_data.validate` command line. They run against the real card
  data and against small made-up records.
* **Fixture tests** (`test_fixture_data.py`, `test_telescope_loader.py`): the invented data
  tree in `tests/fixtures/` (see its README) that covers every card type and opportunity phase
  on a fixed date, 2027-03-15.
* **Card page tests** (`test_card_page_assets.py`, `test_card_page_templates.py`,
  `test_related_links.py`, `test_telescope_card_text.py`): the three card page templates and
  their script, and the text on a Telescope Access card. They check that
  the pages have no inline style or script, that table rows and map markers name an existing
  card and carry the filter data, that "Also see" links resolve (across pages and within one),
  and what a card says (observing mode, process note, header, contacts).
* **Link-check gate tests** (`test_linkcheck_gate.py`): the script that reads
  the link checker's report and decides whether the build passes (working
  links pass, timeouts warn, broken links fail).

## Golden snapshots

`tests/snapshots/<context>.json` holds the output of each loader in
`ikp_data/loaders/` (datasets, telescopes, opportunities, software, IDACs) as
stable JSON, built for the fixed date 2026-09-15. `test_conf_snapshots.py` calls
`build_contexts` and compares each context with its file, so a change to the
loaders that alters any output shows up as a failing test. One more test imports
`conf.py` (with the clock frozen) and checks it produces the same contexts.

Update them **only for an intended, reviewed change** (for example, a data
edit or an approved loader change). Never update them just to make a failing
test pass without understanding the diff:

    tox run -e test -- --update-snapshots

Then review `git diff tests/snapshots/` and commit the files together with
the change that caused them.
