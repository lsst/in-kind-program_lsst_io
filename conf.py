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

html_theme_options = {
    "use_social_cards": False,
}


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
    # 2026-10-16: returns 404. Kept ignored until a replacement link is
    # available. Other vidojevica.aob.rs URLs are now checked.
    r'^https://vidojevica\.aob\.rs/index\.php\?option=com_content&view=article&id=21&Itemid=28$',
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
    # 2026-10-20: NBI LSST IDAC wiki (Denmark IDAC card) -- <error from log>
      # to GitHub Actions runners; works from a browser.
      r'^https://wiki\.nbi\.ku\.dk/lsst_idac/Main_Page$',
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

jinja_contexts = build_contexts(DATA_DIR, today=datetime.date.today())
