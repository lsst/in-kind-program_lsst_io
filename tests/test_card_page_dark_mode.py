"""Checks on the dark-mode colours in docs/_static/ikp/cards.css.

The `:root` block of cards.css holds the light colours as `--ikp-*` variables;
the `html[data-theme=dark]` block redefines the ones that would look wrong on a
dark page. These tests read the file (no browser) and check that:

* every light colour variable has a dark value, or is on a short list of
  exceptions that each give a reason;
* every text colour in the dark block reaches 4.5:1 (WCAG AA) against the
  background it is drawn on, and every map marker reaches 3:1 against the map
  panel and the land; the map key text reaches 4.5:1 on the panel in both themes.

The contrast formula is the WCAG 2 one, written out below so a reviewer can read it.
"""

import re
from pathlib import Path

import pytest

CARDS_CSS = Path(__file__).resolve().parent.parent / "docs" / "_static" / "ikp" / "cards.css"

# The dark theme's own page and card backgrounds (pydata-sphinx-theme). Translucent
# colours in the dark block are blended over one of these before their contrast is measured.
DARK_PAGE_BG = "#14181e"
DARK_CARD_BG = "#222832"

# Light-only colour variables that deliberately have no dark value.
NO_DARK_VALUE_NEEDED = {
    "--ikp-green-on-dark": "already the dark-mode green; the dark block refers to it",
    "--ikp-pill-hover": "the light-mode hover of the expand buttons; dark mode uses --ikp-pill-hover-on-dark",
    "--ikp-pill-hover-on-dark": "already a dark-mode value",
}


# --- Reading the CSS ---------------------------------------------------------------

def read_variables(selector_pattern):
    """The `--ikp-*: value;` pairs of the first block whose selector matches `selector_pattern`."""
    css = re.sub(r"/\*.*?\*/", "", CARDS_CSS.read_text(encoding="utf-8"), flags=re.S)
    block = re.search(selector_pattern + r"\s*\{(.*?)\}", css, flags=re.S | re.M)
    assert block, f"no block matches {selector_pattern}"
    return dict(re.findall(r"(--ikp-[a-z0-9-]+)\s*:\s*([^;]+);", block.group(1)))


LIGHT = read_variables(r"^:root")
DARK = read_variables(r"html\[data-theme=dark\]")


# --- Colour maths ------------------------------------------------------------------

def parse_colour(value, variables):
    """Turn `#rrggbb`, `#rgb`, `rgba(r, g, b, a)` or `var(--name)` into (r, g, b, alpha)."""
    value = value.strip()
    reference = re.fullmatch(r"var\((--[a-z0-9-]+)\)", value)
    if reference:
        return parse_colour(variables[reference.group(1)], variables)
    if value.startswith("#"):
        digits = value[1:]
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16), 1.0)
    rgba = re.fullmatch(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", value)
    assert rgba, f"cannot read the colour {value!r}"
    return (int(rgba.group(1)), int(rgba.group(2)), int(rgba.group(3)), float(rgba.group(4)))


def blend(colour, under):
    """Composite a possibly translucent colour over an opaque one (`under` must be opaque); returns (r, g, b)."""
    r, g, b, alpha = colour
    ur, ug, ub, _ = under
    return tuple(round(alpha * top + (1 - alpha) * bottom) for top, bottom in ((r, ur), (g, ug), (b, ub)))


def luminance(rgb):
    """WCAG relative luminance of an (r, g, b) colour with 0-255 channels."""
    def linear(channel):
        c = channel / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground, background):
    """WCAG contrast ratio of two (r, g, b) colours."""
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def dark_rgb(name_or_hex, over=DARK_PAGE_BG):
    """A dark-mode colour as opaque (r, g, b), blended over `over` if it is translucent.

    A name starting with `--` is looked up in the dark block first, then in `:root`.
    """
    variables = {**LIGHT, **DARK}
    value = variables[name_or_hex] if name_or_hex.startswith("--") else name_or_hex
    return blend(parse_colour(value, variables), parse_colour(over, variables))


# --- Tests -------------------------------------------------------------------------

def is_colour(value):
    return value.strip().startswith(("#", "rgba(", "rgb(")) or value.strip().startswith("var(")


def test_every_light_colour_variable_has_a_dark_value_or_a_reason():
    light_colours = {name for name, value in LIGHT.items() if is_colour(value)}
    missing = light_colours - set(DARK) - set(NO_DARK_VALUE_NEEDED)
    assert not missing, f"no dark value (and no listed reason) for: {sorted(missing)}"


def test_the_exception_list_names_real_light_variables():
    assert set(NO_DARK_VALUE_NEEDED) <= set(LIGHT)


def test_the_dark_block_defines_no_variable_that_light_mode_lacks():
    assert set(DARK) <= set(LIGHT)


# Each entry: (text variable, background variable, what the background sits on).
BANNER_BACKGROUNDS = ["--ikp-green-tint", "--ikp-opp-warning-bg", "--ikp-opp-muted-bg"]
BANNER_TEXTS = [
    "--ikp-text", "--ikp-opp-status-text", "--ikp-opp-deadline-text", "--ikp-green-link",
    "--ikp-milestone-approx", "--ikp-milestone-passed", "--ikp-milestone-passed-label",
    "--ikp-opp-related-text",
]
TEXT_PAIRS = (
    [
        ("--ikp-badge-success-text", "--ikp-badge-success-bg"),
        ("--ikp-badge-muted-text", "--ikp-badge-muted-bg"),
        ("--ikp-badge-warning-text", "--ikp-badge-warning-bg"),
        ("--ikp-badge-danger-text", "--ikp-badge-danger-bg"),
        ("--ikp-also-see-text", "--ikp-also-see-bg"),
        ("--ikp-also-see-text", "--ikp-also-see-bg-hover"),
        ("--ikp-opp-muted-text", "--ikp-opp-muted-bg"),
    ]
    # Banner text colours are checked on all three banner backgrounds, because any
    # banner (normal, warning, muted) can show any of these lines.
    + [(text, bg) for text in BANNER_TEXTS for bg in BANNER_BACKGROUNDS]
)


@pytest.mark.parametrize("text, background", TEXT_PAIRS)
def test_dark_text_on_its_background_reaches_4_5_to_1(text, background):
    # Every colour in TEXT_PAIRS is opaque, so no blending is needed.
    ratio = contrast(dark_rgb(text), dark_rgb(background))
    assert ratio >= 4.5, f"{text} on {background}: {ratio:.2f}:1"


@pytest.mark.parametrize("text, background", [
    ("--ikp-teaser-heading-text", "--ikp-teaser-bg"),
    ("--ikp-teaser-link-text", "--ikp-teaser-bg"),
    ("--ikp-teaser-reason-text", "--ikp-teaser-reason-bg"),
])
def test_dark_teaser_text_reaches_4_5_to_1(text, background):
    # The teaser colours are translucent and sit on the page background; the reason
    # badge also sits on the (blended) teaser background.
    teaser_bg = dark_rgb("--ikp-teaser-bg")
    bg = dark_rgb(background, over="#%02x%02x%02x" % teaser_bg)
    ratio = contrast(dark_rgb(text, over="#%02x%02x%02x" % bg), bg)
    assert ratio >= 4.5, f"{text} on {background}: {ratio:.2f}:1"


def test_dark_siblings_text_reaches_4_5_to_1_on_the_card():
    assert contrast(dark_rgb("--ikp-siblings-text"), dark_rgb(DARK_CARD_BG)) >= 4.5


def test_the_expand_pill_text_reaches_4_5_to_1_on_the_dark_card():
    # The pills draw --ikp-green as their text on the card background.
    assert contrast(dark_rgb("--ikp-green"), dark_rgb(DARK_CARD_BG)) >= 4.5


# --- No colour outside the variables ----------------------------------------------

# `(?<!&)` skips numeric HTML entities such as &#9662;, which are not colours.
COLOUR_LITERAL = re.compile(r"(?<!&)#[0-9a-fA-F]{3,8}\b|\brgba?\(")


def test_cards_css_hard_codes_no_colour_outside_the_variable_blocks():
    css = re.sub(r"/\*.*?\*/", "", CARDS_CSS.read_text(encoding="utf-8"), flags=re.S)
    # Remove the two variable blocks, which are where colours belong.
    css = re.sub(r"^:root\s*\{.*?\}", "", css, flags=re.S | re.M)
    css = re.sub(r"html\[data-theme=dark\]\s*\{.*?\}", "", css, flags=re.S)
    # The one allowed literal: the fade at the foot of a clamped description is an
    # alpha mask (only its opacity matters), not a painted colour.
    css = css.replace("linear-gradient(to bottom, #000 calc(100% - 1.8em), transparent)", "")
    assert not COLOUR_LITERAL.findall(css), f"colour literal outside the variables: {COLOUR_LITERAL.findall(css)}"


PAGES_DIR = CARDS_CSS.parent.parent.parent / "contribution-types"


@pytest.mark.parametrize("path", [
    PAGES_DIR / "contributed-telescope.rst",
    PAGES_DIR / "contributed-datasets.rst",
    PAGES_DIR / "contributed-software.rst",
    CARDS_CSS.with_name("cards.js"),
], ids=lambda path: path.name)
def test_the_templates_and_script_hold_no_colour_literals(path):
    # The Computing Resources page keeps its own inline styles and is not checked.
    assert not COLOUR_LITERAL.findall(path.read_text(encoding="utf-8")), f"{path.name} holds a colour literal"


@pytest.mark.parametrize("marker", [
    "--ikp-map-marker-available", "--ikp-map-marker-past", "--ikp-map-marker-future",
])
@pytest.mark.parametrize("surface", ["--ikp-map-background", "--ikp-map-land"])
def test_dark_map_markers_reach_3_to_1(marker, surface):
    ratio = contrast(dark_rgb(marker), dark_rgb(surface))
    assert ratio >= 3.0, f"{marker} on {surface}: {ratio:.2f}:1"


# --- The map key -------------------------------------------------------------------

@pytest.mark.parametrize("theme, variables", [("light", LIGHT), ("dark", {**LIGHT, **DARK})])
def test_the_map_key_text_reaches_4_5_to_1_on_the_map_panel(theme, variables):
    text = parse_colour(variables["--ikp-map-legend-text"], variables)
    panel = parse_colour(variables["--ikp-map-background"], variables)
    ratio = contrast(text[:3], panel[:3])
    assert ratio >= 4.5, f"{theme}: legend text on the map panel {ratio:.2f}:1"


@pytest.mark.parametrize("marker", [
    "--ikp-map-marker-available", "--ikp-map-marker-past", "--ikp-map-marker-future",
])
@pytest.mark.parametrize("surface", ["--ikp-map-background", "--ikp-map-land"])
def test_light_map_markers_reach_3_to_1(marker, surface):
    """The markers sit on the panel and on the land; the legend's symbols use the same colours."""
    ratio = contrast(parse_colour(LIGHT[marker], LIGHT)[:3], parse_colour(LIGHT[surface], LIGHT)[:3])
    assert ratio >= 3.0, f"{marker} on {surface} (light): {ratio:.2f}:1"


# --- Light-mode contrast and the search box border ---------------------------------

def light_rgb(name):
    """A light-mode colour variable as opaque (r, g, b)."""
    return parse_colour(LIGHT[name], LIGHT)[:3]


@pytest.mark.parametrize("text, background", TEXT_PAIRS)
def test_light_text_on_its_background_reaches_4_5_to_1(text, background):
    # The same pairs as the dark matrix, read from the `:root` block.
    ratio = contrast(light_rgb(text), light_rgb(background))
    assert ratio >= 4.5, f"{text} on {background} (light): {ratio:.2f}:1"


def test_the_light_matrix_covers_the_struck_through_milestone_text():
    for text in ("--ikp-milestone-passed", "--ikp-milestone-approx", "--ikp-milestone-passed-label"):
        for background in BANNER_BACKGROUNDS:
            assert (text, background) in TEXT_PAIRS


@pytest.mark.parametrize("theme, variables, page_background", [
    ("light", LIGHT, "#ffffff"),
    ("dark", {**LIGHT, **DARK}, DARK_PAGE_BG),
])
def test_the_search_box_border_reaches_3_to_1_on_the_page(theme, variables, page_background):
    # A control's border needs 3:1 (WCAG 1.4.11).
    border = parse_colour(variables["--ikp-control-border"], variables)[:3]
    page = parse_colour(page_background, variables)[:3]
    ratio = contrast(border, page)
    assert ratio >= 3.0, f"{theme}: search box border on the page {ratio:.2f}:1"


def test_the_dark_search_box_border_is_unchanged():
    assert DARK["--ikp-control-border"] == "#999"


# --- Jumping to a card: focus and reduced motion -----------------------------------

CARDS_JS = CARDS_CSS.with_name("cards.js")


def test_a_jump_makes_the_card_focusable_and_focuses_it_without_scrolling():
    script = CARDS_JS.read_text(encoding="utf-8")
    assert "setAttribute('tabindex', '-1')" in script
    assert "card.focus({ preventScroll: true })" in script


def test_a_jump_scrolls_instantly_when_reduced_motion_is_asked_for():
    script = CARDS_JS.read_text(encoding="utf-8")
    assert "matchMedia('(prefers-reduced-motion: reduce)')" in script
    assert "'auto'" in script and "'smooth'" in script


def test_the_highlight_fade_is_off_under_reduced_motion():
    css = re.sub(r"/\*.*?\*/", "", CARDS_CSS.read_text(encoding="utf-8"), flags=re.S)
    block = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{(.*?)\}\s*\}", css + "}", flags=re.S)
    assert block, "no reduced-motion media block"
    assert re.search(r"\.ikp-card\.ikp-highlight \.sd-card\s*\{\s*transition:\s*none;", block.group(1))
