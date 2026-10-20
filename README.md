# In-Kind Program website

This is the source for the In-Kind Program website at https://in-kind-program.lsst.io.

## Building the documentation

You need Python to compile the documentation site locally. First, create a Python environment and install the development dependencies into it:

```bash
python -m venv .venv
source .venv/bin/activate
make init
```

To compile the documentation, use tox:

```bash
tox run -e html
```

The compiled documentation will be in `_build/html`.

You can also test formatting and links with other tox environments:

```bash
tox run -e lint,linkcheck
```

The pre-commit hooks, which run in the `lint` environment, also run automatically when you commit changes.
The pre-commit hooks are installed as part of the `make init` command.

## Link checking

In pull requests, the link check fails only on broken links. Timeouts are reported as warnings, because a slow host is not necessarily a dead link.
A few known-bad URLs are ignored in `conf.py`, so a weekly GitHub Actions run (`linkcheck-weekly.yaml`) re-checks everything, ignored URLs included.
To run that full check locally: `IKP_LINKCHECK_FULL=1 tox run -e linkcheck`.

## Card data validation

Every card YAML file under `docs/contribution-types/_data/` must match its schema in `ikp_data/schemas.py`. CI and the pre-commit hook run `tox run -e validate`, so a malformed card (an unknown field, a missing `last_updated`, a misspelled status) fails with a message naming the file and field. Run the same check locally before you commit: `tox run -e validate`.

## Card dates

Each dataset and software card has an explicit `last_updated: 'YYYY-MM-DD'` field in its YAML file. Update the date when the card's content changes. New records must include `last_updated`; a card without it fails validation (`tox run -e validate`).

## CI and preview

This documentation is built with GitHub Actions. The `main` branch reflects the `in-kind-program.lsst.io` site.
Previews of branches are also built and deployed at https://in-kind-program.lsst.io/v.

For more information about writing Rubin user guides, see the [Documenteer documentation](https://documenteer.lsst.io/guides/index.html).
