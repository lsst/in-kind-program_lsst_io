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

## CI and preview

This documentation is built with GitHub Actions. The `main` branch reflects the `in-kind-program.lsst.io` site.
Previews of branches are also built and deployed at https://in-kind-program'.lsst.io/v.

For more information about writing Rubin user guides, see the [Documenteer documentation](https://documenteer.lsst.io/guides/index.html).
