# Tests

All tests run through one entry point:

    tox run -e test

The suite has three parts:

* **Snapshot tests** (`test_conf_snapshots.py`): golden-file tests for the
  card loaders in `ikp_data/loaders/`. See below.
* **Schema, check and validator tests** (`test_schemas.py`): the pydantic
  models in `ikp_data/schemas.py`, the cross-record checks, and the
  `python -m ikp_data.validate` command line. They run against the real card
  data and against small made-up records.
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
