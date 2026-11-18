"""The card page templates must not carry inline styles or scripts.

The Telescope Access, Datasets and Software pages take their CSS and JavaScript
from the shared files docs/_static/ikp/cards.css and cards.js. This test keeps
inline <style> blocks and executable inline <script> blocks from creeping back
into those three templates. A data-only block (`<script type="application/json">`,
used to hand the search text to cards.js) is allowed.

The Computing Resources (IDAC) page is deliberately not checked: it keeps its
own inline style and script.
"""

import re
from pathlib import Path

import pytest

PAGES_DIR = Path(__file__).resolve().parent.parent / "docs" / "contribution-types"
CARD_PAGES = [
    "contributed-telescope.rst",
    "contributed-datasets.rst",
    "contributed-software.rst",
]

# Any <style> tag, and any <script> tag. The script check below then accepts
# the data-only JSON kind.
STYLE_TAG = re.compile(r"<style\b", re.IGNORECASE)
SCRIPT_TAG = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)
JSON_TYPE = re.compile(r"""type\s*=\s*["']application/json["']""", re.IGNORECASE)


@pytest.mark.parametrize("page", CARD_PAGES)
def test_no_inline_style_block(page):
    text = (PAGES_DIR / page).read_text(encoding="utf-8")
    assert not STYLE_TAG.search(text), f"{page} has an inline <style> block; use cards.css"


@pytest.mark.parametrize("page", CARD_PAGES)
def test_no_inline_script_except_json_data(page):
    text = (PAGES_DIR / page).read_text(encoding="utf-8")
    executable = [m.group(0) for m in SCRIPT_TAG.finditer(text) if not JSON_TYPE.search(m.group(1))]
    assert not executable, f"{page} has an inline executable <script>; use cards.js"
