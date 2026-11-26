"""Check the three card pages for accessibility problems that axe-core can find.

Why this exists: the Telescope Access, Contributed Datasets and Contributed
Software pages are built from our own card markup (``ikp-`` classes), from
sphinx-design components, and from the pydata-sphinx-theme chrome around them.
We can fix the first two, but not the third. This script opens the *built* HTML
in headless Chromium, runs axe-core (WCAG 2.0 and 2.1, levels A and AA) on the
whole page in light and dark mode, and sorts every finding by who owns it:

* ``ours``          the article body: anything inside ``<article class="bd-article">``
                    (intro text and links are RST we write, plus our ``ikp-``
                    markup and the ``.sd-card`` card output). We fix these.
                    An ``ikp-`` element or ``.sd-card`` counts as ours wherever it is.
* ``sphinx-design`` ``sd-`` markup that is not inside an ``ikp-`` element or a
                    card. We fix these with CSS, JS or a different component role.
* ``theme``         only chrome outside the article: header and navbar, sidebars,
                    prev/next footer links and the footer. Reported, and may be
                    exempted with a reason (``EXEMPTIONS``).

It also checks "reflow" (WCAG 1.4.10): at a 320 px wide window nothing outside
a data table may need sideways scrolling. The theme's article container
(``.bd-article-container``) scrolls sideways by itself, so the document width
alone never shows an overflow. The check therefore fails if the document is
wider than the window, if the article container scrolls sideways, or if any
element in the article that is not inside an ``.ikp-table-scroll`` wrapper
reaches past the right edge of the window. Tables scroll in their wrapper,
which the WCAG exception for data tables allows. If the container is missing
or no element in the article was examined (the theme's structure changed), the
check fails rather than passing on nothing.

Limits of the reflow check: through the container signal it catches overflow
from absolute, fixed or transformed elements and long words. It misses content
clipped by an ``overflow:hidden`` ancestor, and fixed theme chrome outside
``<article>``. Any other scroller inside the article (a code block, say) is
flagged, which is the safe direction. Only the loaded state and the
expanded-and-sorted state are measured.

Each page is scanned twice per theme: once as loaded, and once "expanded", after
clicking every "Show more" and "Read full description" button and sorting the
first sortable column, so the hidden text and the sorted state (``aria-sort`` and
the arrow) are checked too.

It passes (exit 0) only when every violation is exempt, there are no stale
exemption entries, and there is no reflow overflow. Two kinds of exemption:

* the ``EXEMPTIONS`` list: theme-owned findings only, each with a reason;
* the theme link colour: a ``color-contrast`` finding whose foreground is exactly
  ``THEME_LINK_COLOUR`` and whose ratio is at least ``THEME_COLOUR_MIN_RATIO``
  (3:1) is exempt whatever its owner. It is reported in its own
  "exempt: theme colour" group so it stays visible.

Any other violation fails the run, whoever owns it, including a theme violation
with no exemption. axe "incomplete" items ("needs review") are listed for a
person to judge; they are never exempted and do not fail the run.

Exit codes: 0 pass, 1 findings, 2 the check could not run (missing build
directory or page, theme mode mismatch, Chromium not installed).

What this is not: automated checks find only part of the problems. The claim
that the pages are accessible also rests on keyboard and screen reader checks.

The browser blocks every request that is not ``file://``, so the web font from
Google Fonts is not loaded and the check runs with the fallback font. The report
prints how many requests were blocked.

Usage (build the site first, ``tox -e html``; then ``tox -e a11y``):

    python scripts/a11y_check.py _build/html [--json report.json] [--pages ...]

Pages load straight from ``file://``, so no web server is started. Playwright
and axe are imported inside ``run_browser_scan`` only, so the pure functions
(and their tests) work in an environment without a browser.
"""

import argparse
import json
import re
import sys
from pathlib import Path


class SetupError(Exception):
    """The check could not run (as opposed to running and finding problems)."""


# The pages checked by default, relative to the built HTML directory.
DEFAULT_PAGES = (
    "contribution-types/contributed-telescope.html",
    "contribution-types/contributed-datasets.html",
    "contribution-types/contributed-software.html",
)

# Only the WCAG 2.0 / 2.1 level A and AA rules (no best-practice or AAA rules).
AXE_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa")

THEMES = ("light", "dark")
DESKTOP_VIEWPORT = {"width": 1280, "height": 900}
REFLOW_VIEWPORT = {"width": 320, "height": 800}

OWNER_OURS = "ours"
OWNER_SPHINX_DESIGN = "sphinx-design"
OWNER_THEME = "theme"
OWNERS = (OWNER_OURS, OWNER_SPHINX_DESIGN, OWNER_THEME)
# Owners whose violations we must fix (they fail the run).
OWNERS_WE_FIX = (OWNER_OURS, OWNER_SPHINX_DESIGN)

# Known theme-owned violations that we accept. Each entry is
# (rule_id, selector_substring, reason). A theme-owned violation whose rule id
# matches and whose target selector contains the substring is reported as
# "exempt". An entry that matches nothing is "stale" and fails the run, so the
# list cannot quietly outlive the problem. Only theme-owned items can be
# exempt. Each entry needs a reason; review the list whenever the theme is
# upgraded. (The theme link colour is exempt separately, see THEME_LINK_COLOUR.)
#
# Not an exemption, but a manual verdict: axe lists the search button's keyboard
# shortcut hint (".kbd-shortcut__modifier" in the navbar) as an "incomplete"
# colour-contrast item on every page. It needs a person's judgement; incomplete
# items are never exempted.
EXEMPTIONS: list[tuple[str, str, str]] = [
    (
        "label-content-name-mismatch",
        "search-button",
        "Theme navbar search button: its markup and label are the theme's",
    ),
    (
        "label-content-name-mismatch",
        "theme-switch-button",
        "Theme colour-mode button: its markup and label are the theme's",
    ),
    (
        "color-contrast",
        "bd-navbar-elements",
        "Theme navbar links use the link colour #058B8C (4.13:1 on white)",
    ),
    (
        "color-contrast",
        "prev-next",
        "Theme prev/next footer links use the link colour #058B8C (4.13:1 on white)",
    ),
    (
        "color-contrast",
        'a[href="#"]',
        "Theme sidebar current-page link uses the link colour #058B8C (4.13:1 on white)",
    ),
    (
        "color-contrast",
        'sphinx-doc.org/"]',
        "Theme footer link to sphinx-doc.org uses the link colour #058B8C (4.13:1 on white)",
    ),
    (
        "color-contrast",
        ".theme-version",
        "Theme footer version link uses the link colour #058B8C (4.13:1 on white)",
    ),
]

# The theme's link colour. It is kept by decision, so a colour-contrast finding
# whose foreground is exactly this colour is exempt, whoever owns the node
# (axe reports colours as lower-case hex). It is 4.13:1 on white; 4.5:1 is needed.
THEME_LINK_COLOUR = "#058b8c"
# The exemption has a floor: teal text measured below this ratio is not exempt.
# On white the colour is 4.13:1 and on tinted backgrounds it is lower, but a
# worse result (for example after a theme upgrade) must still fail the run.
THEME_COLOUR_MIN_RATIO = 3.0
THEME_COLOUR_REASON = (
    "theme link colour, kept by decision: 4.13:1 on white, "
    "lower on tinted backgrounds (floor 3:1)"
)

# The two button classes whose click expands hidden card text.
EXPAND_BUTTON_SELECTOR = ".ikp-more-btn, .ikp-expand-btn"

# How many node targets to print per violation in the text report.
MAX_TARGETS_SHOWN = 3


# --------------------------------------------------------------------------
# Pure functions (unit-tested; no browser needed)
# --------------------------------------------------------------------------

# A class or id that starts with "ikp-", in a CSS selector (".ikp-x", "#ikp-x")
# or in HTML attribute text (class="a ikp-x", id="ikp-x").
_IKP_IN_SELECTOR = re.compile(r"[.#]ikp-")
_IKP_IN_HTML = re.compile(r"""(?:class|id)\s*=\s*["'][^"']*\bikp-""")
# sd-card, sd-card-body, ... : output of our card templates.
_SD_CARD_IN_SELECTOR = re.compile(r"\.sd-card\b")
_SD_CARD_IN_HTML = re.compile(r"""class\s*=\s*["'][^"']*\bsd-card\b""")
# Any other sphinx-design class.
_SD_IN_SELECTOR = re.compile(r"\.sd-")
_SD_IN_HTML = re.compile(r"""class\s*=\s*["'][^"']*\bsd-""")
# The theme's article element, class "bd-article" exactly (not "bd-article-container").
_ARTICLE_IN_SELECTOR = re.compile(r"\.bd-article(?![\w-])")
_ARTICLE_IN_HTML = re.compile(r"""class\s*=\s*["'][^"']*(?<![\w-])bd-article(?![\w-])""")


def classify_owner(target: str, html: str, ancestor_markup: str | None = "") -> str:
    """Return who owns the element axe flagged: ours, sphinx-design or theme.

    ``target`` is axe's CSS selector for the node, ``html`` its (possibly
    truncated) outer HTML, and ``ancestor_markup`` the opening tags of its
    ancestors, which the browser step supplies because axe's selector does not
    always name them. ``ancestor_markup=None`` means the browser could not find
    the element; that fails closed as ours, so nothing is hidden as theme.
    The rules, in order:

    1. An ``ikp-`` element or ``.sd-card`` (itself or an ancestor) is ours.
    2. Otherwise ``sd-`` markup is sphinx-design, wherever it is.
    3. Otherwise anything inside the article body is ours (intro text and links
       are RST we write).
    4. Everything else (header, sidebars, prev/next links, footer) is theme.

    When a node is ambiguous this picks ours or sphinx-design, so no issue is
    hidden as "theme".
    """
    if ancestor_markup is None:
        return OWNER_OURS

    own_text = f"{target}\n{html}"
    ancestor_text = ancestor_markup

    if (
        _IKP_IN_SELECTOR.search(own_text)
        or _IKP_IN_HTML.search(own_text)
        or _IKP_IN_HTML.search(ancestor_text)
        or _SD_CARD_IN_SELECTOR.search(own_text)
        or _SD_CARD_IN_HTML.search(own_text)
        or _SD_CARD_IN_HTML.search(ancestor_text)
    ):
        return OWNER_OURS

    if (
        _SD_IN_SELECTOR.search(own_text)
        or _SD_IN_HTML.search(own_text)
        or _SD_IN_HTML.search(ancestor_text)
    ):
        return OWNER_SPHINX_DESIGN

    if (
        _ARTICLE_IN_SELECTOR.search(own_text)
        or _ARTICLE_IN_HTML.search(own_text)
        or _ARTICLE_IN_HTML.search(ancestor_text)
    ):
        return OWNER_OURS

    return OWNER_THEME


def find_exemption(rule_id: str, target: str, exemptions=EXEMPTIONS, fg_color: str = ""):
    """Return the first exemption entry matching this rule and target, or None.

    A ``color-contrast`` entry also requires the measured foreground to be the
    theme link colour, so a theme upgrade to a worse colour is not silently
    exempted.
    """
    if rule_id == "color-contrast" and fg_color != THEME_LINK_COLOUR:
        return None
    for entry in exemptions:
        entry_rule, selector_substring, _reason = entry
        if entry_rule == rule_id and selector_substring in target:
            return entry
    return None


def foreground_color(axe_node: dict) -> str:
    """Return the foreground colour axe measured for a colour-contrast node, or ""."""
    checks = axe_node.get("any", []) + axe_node.get("all", []) + axe_node.get("none", [])
    for check in checks:
        data = check.get("data")
        if isinstance(data, dict) and data.get("fgColor"):
            return str(data["fgColor"]).lower()
    return ""


def contrast_ratio(axe_node: dict):
    """Return the contrast ratio axe measured for a colour-contrast node, or None."""
    checks = axe_node.get("any", []) + axe_node.get("all", []) + axe_node.get("none", [])
    for check in checks:
        data = check.get("data")
        if isinstance(data, dict) and isinstance(data.get("contrastRatio"), (int, float)):
            return float(data["contrastRatio"])
    return None


def apply_exemptions(scans: list[dict], exemptions=EXEMPTIONS) -> list[tuple]:
    """Mark exempt violation nodes in place; return the stale list entries.

    A theme-owned node matching a list entry gets ``exempt_kind = "list"``. Any
    other colour-contrast node whose foreground is the theme link colour gets
    ``exempt_kind = "theme-colour"``, whatever its owner. List entries are
    tried first, so they are not called stale just because the colour rule
    would also cover them. The colour rule needs a measured ratio of at least
    ``THEME_COLOUR_MIN_RATIO``; below it the node stays an open violation.
    Each exempt node gets ``exempt_reason``.
    Incomplete items are never exempted: they are only listed for a verdict.
    """
    used = set()
    for scan in scans:
        for violation in scan["violations"]:
            for node in violation["nodes"]:
                if node["owner"] == OWNER_THEME:
                    entry = find_exemption(
                        violation["id"], node["target"], exemptions, node.get("fg_color", "")
                    )
                    if entry is not None:
                        node["exempt_kind"] = "list"
                        node["exempt_reason"] = entry[2]
                        used.add(entry)
                        continue
                ratio = node.get("contrast_ratio")
                if (
                    violation["id"] == "color-contrast"
                    and node.get("fg_color") == THEME_LINK_COLOUR
                    and ratio is not None
                    and ratio >= THEME_COLOUR_MIN_RATIO
                ):
                    node["exempt_kind"] = "theme-colour"
                    node["exempt_reason"] = THEME_COLOUR_REASON
    return [entry for entry in exemptions if entry not in used]


def count_by_owner(items: list[dict]) -> dict[str, int]:
    """Count all nodes per owner across violations or incomplete items."""
    counts = dict.fromkeys(OWNERS, 0)
    for item in items:
        for node in item["nodes"]:
            counts[node["owner"]] += 1
    return counts


def count_violation_nodes(violations: list[dict]) -> dict:
    """Count violation nodes: open per owner, list-exempt, and theme-colour-exempt per owner."""
    counts = {
        "open": dict.fromkeys(OWNERS, 0),
        "exempt_list": 0,
        "exempt_colour": dict.fromkeys(OWNERS, 0),
        "colour_min_ratio": None,
    }
    for violation in violations:
        for node in violation["nodes"]:
            kind = node.get("exempt_kind")
            if kind == "list":
                counts["exempt_list"] += 1
            elif kind == "theme-colour":
                counts["exempt_colour"][node["owner"]] += 1
                ratio = node.get("contrast_ratio")
                if ratio is not None and (
                    counts["colour_min_ratio"] is None or ratio < counts["colour_min_ratio"]
                ):
                    counts["colour_min_ratio"] = ratio
            else:
                counts["open"][node["owner"]] += 1
    return counts


def skipped_expand_text(skipped: int) -> str:
    """Describe the hidden expand buttons the scan skipped, or "" if there were none."""
    if not skipped:
        return ""
    noun = "button" if skipped == 1 else "buttons"
    return f"{skipped} hidden \"Read full description\" {noun} skipped (the text fits)"


def reflow_failures(reflows: list[dict]) -> list[dict]:
    """Return the reflow results that overflowed."""
    return [result for result in reflows if result["overflow"]]


def decide_exit_code(scans, stale, reflows) -> int:
    """Return 1 if anything remains that is not exempt, otherwise 0.

    Fails on: a violation node that is not exempt (whoever owns it, so a theme
    violation with no exemption fails too), a stale exemption entry, reflow
    overflow, or an expand button that could not be clicked (in either pass). Incomplete items
    never fail the run.
    """
    for scan in scans:
        if any(count_violation_nodes(scan["violations"])["open"].values()):
            return 1
        if scan.get("expand_failures"):
            return 1
    if stale or reflow_failures(reflows):
        return 1
    if any(result.get("expand_failures") for result in reflows):
        return 1
    return 0


def parse_theme_version(footer_text: str) -> str:
    """Return the version number in the footer's "Built with the ... Theme 0.16.1." text."""
    match = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", footer_text or "")
    return match.group(1) if match else "unknown"


def summarize_node_detail(axe_node: dict) -> str:
    """Return a short "why" for one axe node.

    Colour-contrast checks carry numbers in their ``any[].data``: report the
    ratio, foreground, background and font size. For other rules use the first
    message from the node's ``any``, ``all`` or ``none`` checks.
    """
    checks = axe_node.get("any", []) + axe_node.get("all", []) + axe_node.get("none", [])
    for check in checks:
        data = check.get("data")
        if isinstance(data, dict) and "contrastRatio" in data:
            return (
                f"contrast {data['contrastRatio']} (needs {data.get('expectedContrastRatio')}); "
                f"fg {data.get('fgColor')} on bg {data.get('bgColor')}; "
                f"font {data.get('fontSize')}, weight {data.get('fontWeight')}"
            )
    for check in checks:
        if check.get("message"):
            return check["message"]
    return ""


def _format_node_list(nodes: list[dict]) -> str:
    """List the nodes that matter, with an "and N more" tail.

    Every theme node that is not exempt is always listed (never cut), because
    the run fails on it. Other nodes are listed ours first, open before exempt,
    up to MAX_TARGETS_SHOWN. Nodes exempt as the theme colour are only counted
    (in the scan's summary line), not listed.
    """
    def must_show(node):
        return node["owner"] == OWNER_THEME and not node.get("exempt_kind")

    listed_nodes = [n for n in nodes if n.get("exempt_kind") != "theme-colour"]
    always = [n for n in listed_nodes if must_show(n)]
    others = sorted(
        (n for n in listed_nodes if not must_show(n)),
        key=lambda n: (bool(n.get("exempt_kind")), OWNERS.index(n["owner"])),
    )
    shown = always + others[:MAX_TARGETS_SHOWN]
    lines = []
    if not shown and nodes:
        return f"      (all {len(nodes)} nodes exempt as the theme colour)"
    for node in shown:
        line = f"      - [{node['owner']}] {node['target']}"
        if node.get("exempt_kind") == "list":
            line += f"  (exempt: {node['exempt_reason']})"
        lines.append(line)
        if node.get("detail"):
            lines.append(f"          why: {node['detail']}")
    hidden = len(others) - MAX_TARGETS_SHOWN
    if hidden > 0:
        lines.append(f"      ... and {hidden} more")
    return "\n".join(lines)


def _theme_counts_text(counts: dict) -> str:
    return f"{counts['exempt_list']} exempt, {counts['open'][OWNER_THEME]} not exempt"


def _colour_counts_text(counts: dict) -> str:
    by_owner = ", ".join(f"{o} {counts['exempt_colour'][o]}" for o in OWNERS)
    text = f"{sum(counts['exempt_colour'].values())} ({by_owner})"
    if counts["colour_min_ratio"] is not None:
        text += f"; lowest ratio {counts['colour_min_ratio']}:1"
    return text


def format_report(run_info: dict, scans, stale, reflows, exit_code) -> str:
    """Return the readable text report.

    ``run_info`` has ``axe_version``, ``theme_version`` and ``blocked_requests``
    (a list of URLs the browser refused to load).
    """
    blocked = run_info.get("blocked_requests", [])
    lines = [
        f"axe-core {run_info.get('axe_version', 'unknown')}; "
        f"pydata-sphinx-theme {run_info.get('theme_version', 'unknown')}; "
        f"tags: {', '.join(AXE_TAGS)}",
        f"Blocked non-file requests: {run_info.get('blocked_request_count', len(blocked))} "
        f"({len(blocked)} distinct URL(s); the check runs with the fallback font)",
        "",
    ]

    total = {
        "exempt_list": 0,
        "theme_open": 0,
        "colour": dict.fromkeys(OWNERS, 0),
        "min_ratio": None,
    }
    for scan in scans:
        lines.append(f"== {scan['page']} ({scan['theme']} mode, {scan['state']} state) ==")
        counts = count_violation_nodes(scan["violations"])
        incomplete_counts = count_by_owner(scan["incomplete"])
        total["exempt_list"] += counts["exempt_list"]
        total["theme_open"] += counts["open"][OWNER_THEME]
        for owner in OWNERS:
            total["colour"][owner] += counts["exempt_colour"][owner]
        ratio = counts["colour_min_ratio"]
        if ratio is not None and (total["min_ratio"] is None or ratio < total["min_ratio"]):
            total["min_ratio"] = ratio
        lines.append(
            f"  violations (nodes): ours={counts['open'][OWNER_OURS]} open, "
            f"sphinx-design={counts['open'][OWNER_SPHINX_DESIGN]} open, "
            f"theme: {_theme_counts_text(counts)}"
        )
        lines.append(f"  exempt: theme colour: {_colour_counts_text(counts)}")
        lines.append(
            "  needs review (nodes): "
            + ", ".join(f"{owner}={incomplete_counts[owner]}" for owner in OWNERS)
        )
        if scan.get("expand_failures"):
            lines.append(f"  FAIL: {scan['expand_failures']} expand button(s) could not be clicked")
        elif scan["state"] == "expanded":
            lines.append(f"  expand buttons clicked: {scan.get('expand_clicked', 0)}")
            skipped_line = skipped_expand_text(scan.get("expand_skipped", 0))
            if skipped_line:
                lines.append(f"  {skipped_line}")
            sort_text = "yes" if scan.get("sorted_first_column") else "no sortable column"
            lines.append(f"  first column sorted: {sort_text}")
        for violation in scan["violations"]:
            lines.append(
                f"  VIOLATION {violation['id']} ({violation['impact']}): "
                f"{violation['help']}"
            )
            lines.append(_format_node_list(violation["nodes"]))
        for item in scan["incomplete"]:
            lines.append(
                f"  NEEDS REVIEW {item['id']} ({item['impact']}): {item['help']}"
            )
            lines.append(_format_node_list(item["nodes"]))
        lines.append("")

    lines.append("== Reflow at 320 px wide (light mode) ==")
    for result in reflows:
        label = f"{result['page']} ({result['state']} state)"
        if result.get("expand_failures"):
            lines.append(
                f"  FAIL {label}: {result['expand_failures']} expand button(s) could not be clicked"
            )
        if result["overflow"]:
            lines.append(
                f"  FAIL {label}: {result.get('description') or 'overflow'}"
            )
        else:
            lines.append(f"  ok   {label}")
    lines.append("")

    lines.append("== Exemptions (all scans) ==")
    lines.append(
        f"  theme: {total['exempt_list']} exempt, {total['theme_open']} not exempt"
    )
    colour_by_owner = ", ".join(f"{o} {total['colour'][o]}" for o in OWNERS)
    colour_text = f"  exempt: theme colour: {sum(total['colour'].values())} ({colour_by_owner})"
    if total["min_ratio"] is not None:
        colour_text += f"; lowest ratio {total['min_ratio']}:1"
    lines.append(colour_text)
    lines.append(f"  {len(stale)} stale entr(ies).")
    for rule_id, selector_substring, reason in stale:
        lines.append(f"  STALE: ({rule_id}, {selector_substring!r}) {reason}")
    lines.append("")

    lines.append(f"Result: {'FAIL' if exit_code else 'PASS'} (exit {exit_code})")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Browser step (needs Playwright and axe-playwright-python)
# --------------------------------------------------------------------------

# Runs in the page: the opening tags (class and id only) of every ancestor of
# the element matching `selector`, joined into one string for classify_owner.
# Returns null when the element cannot be found, so the caller fails closed.
_ANCESTOR_MARKUP_JS = """
(selector) => {
  let element = null;
  try { element = document.querySelector(selector); } catch (e) { return null; }
  if (!element) return null;
  const parts = [];
  while (element && element.parentElement) {
    element = element.parentElement;
    parts.push('<x class="' + (element.getAttribute("class") || "") +
               '" id="' + (element.id || "") + '">');
  }
  return parts.join(" ");
}
"""

# Runs in the page: measures the three overflow signals the reflow check uses.
# Elements inside an ``.ikp-table-scroll`` wrapper are skipped (they scroll in
# their own box), as are zero-size and display:none elements. Only the innermost
# offenders are listed: an element is dropped when a child also overflows.
_REFLOW_MEASURE_JS = """
() => {
  const windowWidth = window.innerWidth;
  const container = document.querySelector(".bd-article-container");
  const describe = (element) => {
    const classes = (element.getAttribute("class") || "").trim().split(/\\s+/)
      .filter(Boolean).join(".");
    return {
      tag: element.tagName.toLowerCase(),
      classes: classes,
      right: Math.round(element.getBoundingClientRect().right),
    };
  };
  const overflowing = [];
  let elementsChecked = 0;
  for (const element of document.querySelectorAll("article *")) {
    if (element.closest(".ikp-table-scroll")) continue;
    elementsChecked += 1;
    const box = element.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) continue;
    if (getComputedStyle(element).display === "none") continue;
    if (box.right > windowWidth + 1) overflowing.push(element);
  }
  const innermost = overflowing.filter(
    (element) => !overflowing.some((other) => other !== element && element.contains(other))
  );
  return {
    document_scroll_width: document.documentElement.scrollWidth,
    window_width: windowWidth,
    container_found: container !== null,
    elements_checked: elementsChecked,
    container_scroll_width: container ? container.scrollWidth : null,
    container_client_width: container ? container.clientWidth : null,
    offenders: innermost.map(describe),
  };
}
"""

# How many offending elements the report names.
MAX_REPORTED_OFFENDERS = 5


def evaluate_reflow(measurement: dict) -> tuple[bool, str]:
    """Decide the reflow result from the numbers measured in the page.

    ``measurement`` has the keys of ``_REFLOW_MEASURE_JS``. Returns
    ``(overflow, description)``: ``overflow`` is True if the page fails, and
    ``description`` says why (empty when it passes). Pure, so it is unit-tested
    without a browser.
    """
    reasons = []
    # A theme change that removes the container or the article must fail the
    # check (not raise a setup error), because a pass would mean nothing.
    if not measurement["container_found"]:
        reasons.append(
            "the theme's article container was not found, so overflow can't be measured"
        )
    if measurement["elements_checked"] == 0:
        reasons.append(
            "no elements were examined in the article, so overflow can't be measured"
        )
    # Same 1 px tolerance as the container and element checks, for sub-pixel rounding.
    if measurement["document_scroll_width"] > measurement["window_width"] + 1:
        reasons.append(
            f"the document is {measurement['document_scroll_width']} px wide "
            f"in a {measurement['window_width']} px window"
        )
    container_scroll = measurement.get("container_scroll_width")
    container_client = measurement.get("container_client_width")
    if measurement["container_found"] and container_scroll > container_client + 1:
        reasons.append(
            f"the article container scrolls sideways "
            f"(scrollWidth {container_scroll} > clientWidth {container_client})"
        )
    offenders = measurement.get("offenders") or []
    if offenders:
        named = ", ".join(
            f"{o['tag']}{'.' + o['classes'] if o['classes'] else ''} (right edge {o['right']} px)"
            for o in offenders[:MAX_REPORTED_OFFENDERS]
        )
        more = len(offenders) - MAX_REPORTED_OFFENDERS
        suffix = f" and {more} more" if more > 0 else ""
        reasons.append(f"outside a table wrapper, past the window edge: {named}{suffix}")
    return bool(reasons), "; ".join(reasons)


_THEME_VERSION_JS = """
() => { const el = document.querySelector(".theme-version"); return el ? el.textContent : ""; }
"""


def _new_page(browser, theme: str, viewport: dict, blocked: list):
    """Open a page for one theme. Requests other than file:// are blocked.

    The URL of each blocked request is appended to ``blocked``.
    """
    context = browser.new_context(
        viewport=viewport, reduced_motion="reduce", color_scheme=theme
    )
    # pydata-sphinx-theme's "auto" mode follows the emulated colour scheme.
    context.add_init_script(
        "try { localStorage.setItem('mode', 'auto'); } catch (e) {}"
    )
    page = context.new_page()

    def allow_files_only(route):
        if route.request.url.startswith("file://"):
            route.continue_()
        else:
            blocked.append(route.request.url)
            route.abort()

    page.route("**/*", allow_files_only)
    return page


def _open(page, html_dir: Path, relative: str, expected_theme: str | None = None):
    """Load a page and wait for fonts; check the colour mode if one is expected."""
    page.goto((html_dir / relative).resolve().as_uri(), wait_until="load")
    page.evaluate("document.fonts.ready")
    if expected_theme is not None:
        found = page.evaluate("document.documentElement.dataset.theme")
        if found != expected_theme:
            raise SetupError(
                f"{relative}: expected html data-theme {expected_theme!r}, found {found!r}"
            )


def _expand_all(page) -> tuple[int, int, int]:
    """Click every visible "Show more" and "Read full description" button (the page's own JS runs).

    Returns (clicked, failed, skipped). A hidden "Read full description" button
    is skipped, not counted as a failure: the page hides it when the
    description fits in its clamp, so there is nothing to reveal. Only that
    button may be hidden. A hidden "Show more details" button still goes to the
    click and fails, because the page always shows those once its script runs,
    so a hidden one means the script did not. "Clicked" proves the click
    landed, not that the content expanded; a later PR will assert
    ``aria-expanded`` for that.
    """
    buttons = page.locator(EXPAND_BUTTON_SELECTOR)
    clicked = failed = skipped = 0
    for index in range(buttons.count()):
        button = buttons.nth(index)
        may_be_hidden = button.evaluate("b => b.classList.contains('ikp-expand-btn')")
        if may_be_hidden and not button.is_visible():
            skipped += 1
            continue
        try:
            buttons.nth(index).click(timeout=3000)
            clicked += 1
        except Exception:  # not clickable: count it and go on
            failed += 1
    return clicked, failed, skipped


def _sort_first_column(page) -> tuple[bool, bool]:
    """Click the first sortable column header's button, if the page has one.

    Returns (clicked, failed). A page with no sortable header returns
    (False, False). A button that exists but cannot be clicked returns
    (False, True), and the caller counts it like a failed expand click; so
    does a theme back-to-top button that stays visible after the scroll back.
    """
    buttons = page.locator("th[data-sort] button")
    if buttons.count() == 0:
        return False, False
    try:
        buttons.first.click(timeout=3000)
        # Clicking scrolls the page, which makes the theme's back-to-top button
        # appear. Scroll to the top, where the theme hides it, so both scans see
        # the page in the same position. That button is therefore not scanned;
        # it is theme chrome with a known contrast shortfall (white on #ed4c4c,
        # 3.65:1), noted in the README.
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_selector("#pst-back-to-top", state="hidden", timeout=3000)
        return True, False
    except Exception:  # not clickable: report it and go on
        return False, True


def _simplify_nodes(page, nodes: list[dict]) -> list[dict]:
    """Turn axe nodes into plain dicts, each with its owner category."""
    simplified = []
    for node in nodes:
        target = " ".join(str(part) for part in node["target"])
        html = node.get("html", "")
        # None (element not found) makes classify_owner fail closed as "ours".
        ancestors = page.evaluate(_ANCESTOR_MARKUP_JS, node["target"][-1])
        simplified.append(
            {
                "target": target,
                "html": html,
                "owner": classify_owner(target, html, ancestors),
                "failure_summary": node.get("failureSummary", ""),
                "detail": summarize_node_detail(node),
                "fg_color": foreground_color(node),
                "contrast_ratio": contrast_ratio(node),
            }
        )
    return simplified


def _simplify_results(page, axe_items: list[dict]) -> list[dict]:
    """Turn axe violations or incomplete items into plain, JSON-ready dicts."""
    return [
        {
            "id": item["id"],
            "impact": item.get("impact") or "n/a",
            "help": item["help"],
            "help_url": item.get("helpUrl", ""),
            "nodes": _simplify_nodes(page, item["nodes"]),
        }
        for item in axe_items
    ]


def _reflow_result(page, relative: str, state: str, expand_failures: int = 0) -> dict:
    """Measure horizontal overflow on the already-loaded page."""
    overflow, description = evaluate_reflow(page.evaluate(_REFLOW_MEASURE_JS))
    return {
        "page": relative,
        "state": state,
        "overflow": overflow,
        "description": description,
        "expand_failures": expand_failures,
    }


def run_browser_scan(html_dir: Path, pages: list[str]):
    """Run axe (load and expanded states, light and dark) and the 320 px reflow check.

    The expanded state also has the first sortable column sorted.

    Returns ``(run_info, scans, reflows)``; ``run_info`` has the axe-core and
    theme versions and the list of blocked requests.
    """
    # Imported here so the rest of this module works without a browser.
    try:
        from axe_playwright_python.sync_playwright import Axe
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise SetupError(
            f"Playwright or axe-playwright-python is not installed ({error}). "
            "Run this through tox: tox -e a11y"
        ) from error

    axe = Axe()
    axe_options = {
        "runOnly": {"type": "tag", "values": list(AXE_TAGS)},
        "resultTypes": ["violations", "incomplete"],
    }
    blocked: list[str] = []
    scans, reflows = [], []
    run_info = {"axe_version": "unknown", "theme_version": "unknown"}

    def scan_page(page, relative, theme, state, clicked=0, failed=0, sorted_first=False, skipped=0):
        response = axe.run(page, options=axe_options).response
        run_info["axe_version"] = response.get("testEngine", {}).get("version", "unknown")
        scans.append(
            {
                "page": relative,
                "theme": theme,
                "state": state,
                "violations": _simplify_results(page, response["violations"]),
                "incomplete": _simplify_results(page, response["incomplete"]),
                "expand_clicked": clicked,
                "expand_failures": failed,
                "expand_skipped": skipped,
                "sorted_first_column": sorted_first,
            }
        )

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as error:
            if "Executable doesn't exist" in str(error) or "playwright install" in str(error):
                raise SetupError(
                    "Chromium for Playwright is not installed. Install it once with: "
                    ".tox/a11y/bin/python -m playwright install chromium"
                ) from error
            raise

        for theme in THEMES:
            page = _new_page(browser, theme, DESKTOP_VIEWPORT, blocked)
            for relative in pages:
                _open(page, html_dir, relative, expected_theme=theme)
                if run_info["theme_version"] == "unknown":
                    run_info["theme_version"] = parse_theme_version(
                        page.evaluate(_THEME_VERSION_JS)
                    )
                scan_page(page, relative, theme, "load")
                clicked, failed, skipped = _expand_all(page)
                sorted_first, sort_failed = _sort_first_column(page)
                failed += sort_failed
                # Park the mouse so no button is measured in its hover state.
                page.mouse.move(0, 0)
                scan_page(page, relative, theme, "expanded", clicked, failed, sorted_first, skipped)
            page.context.close()

        page = _new_page(browser, "light", REFLOW_VIEWPORT, blocked)
        for relative in pages:
            _open(page, html_dir, relative)
            reflows.append(_reflow_result(page, relative, "load"))
            _clicked, failed, _skipped = _expand_all(page)
            _sorted, sort_failed = _sort_first_column(page)
            failed += sort_failed
            reflows.append(_reflow_result(page, relative, "expanded", failed))
        page.context.close()
        browser.close()

    run_info["blocked_requests"] = sorted(set(blocked))
    run_info["blocked_request_count"] = len(blocked)
    return run_info, scans, reflows


def main(argv=None) -> int:
    """Run the check, print the report, and return the exit status (0, 1 or 2)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("html_dir", type=Path, help="built HTML directory, e.g. _build/html")
    parser.add_argument("--json", type=Path, metavar="OUT", help="also write a JSON report")
    parser.add_argument(
        "--pages",
        nargs="+",
        default=list(DEFAULT_PAGES),
        help="pages relative to html_dir (default: the three card pages)",
    )
    args = parser.parse_args(argv)

    if not args.html_dir.is_dir():
        print(f"ERROR: build directory not found: {args.html_dir}")
        print("Build the site first (tox -e html).")
        return 2
    missing = [p for p in args.pages if not (args.html_dir / p).is_file()]
    if missing:
        print(f"ERROR: page(s) not found under {args.html_dir}: {', '.join(missing)}")
        print("Build the site first (tox -e html).")
        return 2

    try:
        run_info, scans, reflows = run_browser_scan(args.html_dir, args.pages)
    except SetupError as error:
        print(f"ERROR: {error}")
        return 2
    except Exception as error:  # navigation, axe injection, browser launch ...
        print(f"ERROR: the browser scan failed: {type(error).__name__}: {error}")
        return 2

    stale = apply_exemptions(scans)
    if args.pages != list(DEFAULT_PAGES):
        # With a subset of pages an entry may look unused only because its page
        # was skipped, so do not call it stale.
        stale = []
    exit_code = decide_exit_code(scans, stale, reflows)

    print(format_report(run_info, scans, stale, reflows, exit_code))
    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    **run_info,
                    "tags": list(AXE_TAGS),
                    "scans": scans,
                    "reflow": reflows,
                    "stale_exemptions": [list(entry) for entry in stale],
                    "exit_code": exit_code,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
