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

## Local preview switches

Two environment variables let you preview states of the Contributed pages that the live data can't show. They are for **local previews only**:

- `IKP_TODAY=YYYY-MM-DD` builds the pages as if that were today's date (for example, to see an opportunity banner that has not opened yet).
- `IKP_DATA_DIR=<folder>` builds the pages from another `_data` folder, such as the test data in `tests/fixtures/docs/contribution-types/_data` (see `tests/fixtures/README.md`).

For example:

```bash
IKP_DATA_DIR=tests/fixtures/docs/contribution-types/_data IKP_TODAY=2027-03-15 \
    sphinx-build -E -b html -d _build/doctrees-preview -c . docs _build/html-preview
```

Use `-E` (a fresh environment) with them, so Sphinx doesn't reuse pages cached from a build with different data. A preview build prints one line, `IKP preview override: ...`, naming what is overridden. The build refuses to start if either switch is set while `CI` or `GITHUB_ACTIONS` is set, so a preview can't be published by mistake. A relative `IKP_DATA_DIR` is relative to the folder you run the build from. A custom `IKP_DATA_DIR` should have the same layout as the real one (`docs/contribution-types/_data`, with `docs/_static/world-outline.svg` two levels up), or the map outline will be empty.

## Link checking

In pull requests, the link check fails only on broken links. Timeouts are reported as warnings, because a slow host is not necessarily a dead link.
A few known-bad URLs are ignored in `conf.py`. A weekly GitHub Actions run (`linkcheck-weekly.yaml`) re-checks every link, including the ignored ones.
To run that full check locally, use `IKP_LINKCHECK_FULL=1 tox run -e linkcheck`.

## Accessibility check

`scripts/a11y_check.py` opens the Telescope Access, Contributed Datasets and Contributed Software pages from a built site in headless Chromium, in light and dark mode, and runs axe-core (WCAG 2.0 and 2.1, levels A and AA) on each whole page. It also checks reflow at 320 px wide: the document and the article container must not scroll sideways, and nothing outside a table's `ikp-table-scroll` wrapper may reach past the window edge (the tables may scroll in their own box).
Build the site first, then run the check:

```bash
tox run -e html
tox run -e a11y            # or: tox run -e a11y -- path/to/other/html
```

The check is not part of the default `tox` run, because it needs a browser. If Playwright says Chromium is missing, install it once with `.tox/a11y/bin/python -m playwright install chromium`. The browser blocks every request that is not a local file, so the web font is not loaded and the check runs with the fallback font. Add `--json report.json` to the script to keep a machine-readable report. The check can also be started by hand from the Actions tab ("Accessibility check").

Each page is scanned as loaded and again "expanded" (after every "Show more" and "Read full description" button is clicked and the first sortable column is sorted), in light and dark mode. Both scans run at the top of the page, so the theme's back-to-top button (shown only while the page is scrolled) is not scanned; it is theme chrome, white on `#ED4C4C` at 3.65:1. Each finding is sorted by owner:

- **ours**: anything inside the article body, including the intro text and its links, plus our `ikp-` markup and the cards (`.sd-card`). We fix these.
- **sphinx-design**: `sd-` components that are not inside an `ikp-` element or a card. We fix these too, with CSS, JavaScript or a different component role.
- **theme**: only the chrome outside the article (header, navigation, sidebars, prev/next links, footer).

The run fails if any violation is not exempt (including a theme one), if a page overflows at 320 px (see above), if an exemption entry is stale, or if an expand button cannot be clicked. Exit code 2 means the check could not run (for example a missing build or browser). Two kinds of exemption exist:

- The `EXEMPTIONS` list at the top of the script holds theme findings we accept, each with the rule id, a part of the selector and the reason. An entry that no longer matches anything is reported as stale, so the list cannot outlive the problem. Review the list whenever the theme is upgraded.
- A colour-contrast finding whose text colour is exactly the theme's link colour (`#058B8C`, 4.13:1 on white) is exempt wherever it appears (as long as the measured ratio is at least 3:1), and is counted in its own "exempt: theme colour" group so it stays visible.

Items axe marks "needs review" are listed for a person to judge and are never exempted; today these are colour-contrast items on the navbar search button's keyboard-shortcut hint, the sort arrow in a sorted table header, and the arrows in the "Show more" buttons and "Also see" links. Our arrows are symbols in the colour of the text beside them, which pass when measured. The check passes on live data today. axe cannot see every problem (for example whether a control works from the keyboard), so keyboard and screen reader checks are still needed.

## Card data validation

Every card YAML file under `docs/contribution-types/_data/` must match its schema in `ikp_data/schemas.py`. CI runs `tox run -e validate`, and the pre-commit hook runs the same check. A malformed card (for example, one with an unknown field, a missing `last_updated`, or a misspelled status) fails with a message that names the file and the field. Run the check locally before you commit with `tox run -e validate`.

## Card dates

Each dataset and software card has an explicit `last_updated: 'YYYY-MM-DD'` field in its YAML file. Update the date whenever the card's content changes. New records must include `last_updated`. A card without it fails validation (`tox run -e validate`).

## CI and preview

This documentation is built with GitHub Actions. The `main` branch reflects the `in-kind-program.lsst.io` site.
Previews of branches are also built and deployed at https://in-kind-program.lsst.io/v.

For more information about writing Rubin user guides, see the [Documenteer documentation](https://documenteer.lsst.io/guides/index.html).
