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
A few known-bad URLs are ignored in `conf.py`. A weekly GitHub Actions run (`linkcheck-weekly.yaml`) re-checks every link, including the ignored ones.
To run that full check locally, use `IKP_LINKCHECK_FULL=1 tox run -e linkcheck`.

## Card data validation

Every card YAML file under `docs/contribution-types/_data/` must match its schema in `ikp_data/schemas.py`. CI runs `tox run -e validate`, and the pre-commit hook runs the same check. A malformed card (for example, one with an unknown field, a missing `last_updated`, or a misspelled status) fails with a message that names the file and the field. Run the check locally before you commit with `tox run -e validate`.

## Card dates

Each dataset and software card has an explicit `last_updated: 'YYYY-MM-DD'` field in its YAML file. Update the date whenever the card's content changes. New records must include `last_updated`. A card without it fails validation (`tox run -e validate`).

## CI and preview

This documentation is built with GitHub Actions. The `main` branch reflects the `in-kind-program.lsst.io` site.
Previews of branches are also built and deployed at https://in-kind-program.lsst.io/v.

For more information about writing Rubin user guides, see the [Documenteer documentation](https://documenteer.lsst.io/guides/index.html).
