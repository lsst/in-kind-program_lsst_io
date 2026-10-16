# Golden-snapshot tests

`tests/snapshots/<context>.json` holds the output of each loader in `conf.py`
(datasets, telescopes, opportunities, software, IDACs) as stable JSON, with
the date frozen at 2026-09-15. `test_conf_snapshots.py` rebuilds the
contexts and compares them with these files. They exist so the loader refactor
(M04) can be shown to change nothing.

Run them: `tox run -e test`

Update them **only for an intended, reviewed change** (for example, a data
edit or an approved loader change). Never to make a failing test pass
without understanding the diff:

    tox run -e test -- --update-snapshots

Then review `git diff tests/snapshots/` and commit the files together with
the change that caused them.
