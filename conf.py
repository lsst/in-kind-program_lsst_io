import datetime
import os
import sys
from pathlib import Path

from documenteer.conf.guide import *  # noqa: F401 F403

# This folder holds the ikp_data package. Sphinx is run with `-c .` (conf dir)
# separate from the docs source dir and does not put the conf dir on sys.path
# itself, so add it explicitly before importing the package.
CONF_DIR = Path(__file__).parent
sys.path.insert(0, str(CONF_DIR))

from ikp_data.loaders import build_contexts  # noqa: E402
from ikp_data.preview import resolve_preview_settings  # noqa: E402

html_theme_options = {
    "use_social_cards": False,
}

# Shared styles and script for the card pages (Telescope Access, Datasets,
# Software). Append to Documenteer's lists rather than replacing them, so its
# own theme CSS and script stay. Sphinx adds these files to every page of the
# site, so both files only act on elements that the card pages use. The static
# path is relative to the conf directory (the repository root). These appends
# must stay last: the card styles rely on loading after the theme and
# sphinx-design CSS.
html_static_path += ["docs/_static/ikp"]
html_css_files += ["cards.css"]
# `defer` makes the browser run the script after the page has been parsed.
html_js_files += [("cards.js", {"defer": "defer"})]


# ----------------------------------------------------------------------------
# Linkcheck settings (tuned 2026-10-16)
#
# Ignored URLs below will be re-tested by a planned weekly full link check, so
# an entry here hides a link from the PR build only, not forever.
# ----------------------------------------------------------------------------

# 2026-10-16: Sphinx 8.1.3 does not retry timeouts, and a timeout fails the
# build. Documenteer's preset is 15 s; slow-but-working hosts (e.g. LBT) need
# more headroom.
linkcheck_timeout = 30

# 2026-10-16: extend (not replace) so Documenteer's preset entries (e.g. ^https://ls.st/)
# are kept instead of being replaced. Each pattern is an anchored exact-URL
# regex (re.escape style) for a URL actually used on the site today, so any
# new link on the same host is still checked. Add a URL here only when it is
# known-broken for a documented reason.
#
# Set IKP_LINKCHECK_FULL (to anything except "", "0", "false" or "no", in any
# letter case) for a "full" run: the
# project's ignore entries below are skipped so every ignored URL is re-tested
# (a link that was ignored for a transient reason can then be noticed when it
# recovers, or when it breaks for a new reason), and retries/timeout are raised
# so slow hosts get a fair chance. Documenteer's preset ignores always stay.
# Normal (pull request) builds are unaffected.
_LINKCHECK_FULL = os.environ.get("IKP_LINKCHECK_FULL", "").strip().lower() not in (
    "",
    "0",
    "false",
    "no",
)
if _LINKCHECK_FULL:
    linkcheck_retries = 3
    linkcheck_timeout = 60

_project_linkcheck_ignore = [
    # 2026-11-17: Mt John Observatory wiki (McLellan and Nishimura telescope
    # cards). The university moved its wiki: this address now redirects to the
    # new wiki's front page, and GitHub Actions runners get 403. Ignored until
    # the observatory's new page is found and the cards are updated.
    r'^https://wiki\.canterbury\.ac\.nz/pages/viewpage\.action\?pageId=152307302$',
    # 2026-10-16: WISeREP (NOT telescope card) returns 403 to GitHub Actions
    # runners even with a browser User-Agent, though it works from a desktop.
    # The block is by network, not by agent string, so it can't be fixed here.
    r'^https://www\.wiserep\.org/$',
    # 2026-10-16: SALT (SZA-SAA-S1 telescope card) -- incomplete TLS
    # certificate chain; browsers tolerate it but Python's ssl rejects it
    # (CERTIFICATE_VERIFY_FAILED).
    r'^https://astronomers\.salt\.ac\.za/$',
    r'^https://astronomers\.salt\.ac\.za/instruments/$',
    r'^https://astronomers\.salt\.ac\.za/proposals/$',
    r'^https://astronomers\.salt\.ac\.za/software/$',
    # 2026-10-16: INAF SIPGI proposal tool (LBT card) -- incomplete TLS
    # certificate chain (CERTIFICATE_VERIFY_FAILED in Python's ssl).
    r'^https://pandora\.lambrate\.inaf\.it/sipgi/$',
    # 2026-10-16: ADS abstract pages (SWE-STK-S4 dataset card, UKD-UKD-S17
    # software card) return 405 to automated requests (WAF).
    r'^https://ui\.adsabs\.harvard\.edu/abs/2025A%26A\.\.\.694A\.\.\.1R/abstract$',
    r'^https://ui\.adsabs\.harvard\.edu/abs/2026MNRAS\.547ag360C$',
    # 2026-10-20: NBI LSST IDAC wiki (Denmark IDAC card) returns an error to
    # GitHub Actions runners; it works from a browser.
    r'^https://wiki\.nbi\.ku\.dk/lsst_idac/Main_Page$',
    # 2026-10-20: Zenodo (contributed software and dataset cards) returns 403
    # to GitHub Actions runners (bot blocking); links work from a browser.
    # Covers zenodo.org pages and Zenodo DOIs, which redirect there.
    r'^https://zenodo\.org/',
    r'^https://doi\.org/10\.5281/zenodo\.',
    # 2026-10-20: project.lsst.org is down because of a vulnerability.
    r'^https://project.lsst.org/$',
    # 2026-10-20: SER-SAG data link, ignored until the reason it fails is understood.
    r'^https://ser-sag\.pmf\.kg\.ac\.rs:8081/agn_catalogue\.php/?$',
]

# Only the PR/normal build honours the project's ignore list (see above).
if not _LINKCHECK_FULL:
    linkcheck_ignore += _project_linkcheck_ignore


# ----------------------------------------------------------------------------
# Card data for the Jinja templates
#
# The loaders that turn the YAML files in docs/contribution-types/_data/ into
# the data each page renders live in the ikp_data package (ikp_data/loaders/).
# `sphinx_jinja` (enabled by Documenteer) reads `jinja_contexts`, a dict of
# context name -> data for the .rst templates.
# ----------------------------------------------------------------------------
DATA_DIR = CONF_DIR / "docs" / "contribution-types" / "_data"


# Local preview switches (IKP_TODAY, IKP_DATA_DIR): see ikp_data/preview.py.
# They raise an error, and so stop the build, if set in CI. When one is active
# the build prints a single line naming it.
_preview = resolve_preview_settings(
    os.environ, default_data_dir=DATA_DIR, real_today=datetime.date.today()
)
if _preview.notice:
    print(_preview.notice, flush=True)

jinja_contexts = build_contexts(_preview.data_dir, today=_preview.today)
