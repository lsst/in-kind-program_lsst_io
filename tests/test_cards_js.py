"""Source-level checks on how cards.js moves focus when a visitor jumps to a card.

These tests read the `highlightCard` function in docs/_static/ikp/cards.js as
text. They only confirm the pieces are present and in the right order. The
behaviour itself (focus lands on the card, the scroll is instant under reduced
motion, the attribute is gone after blur) is checked in a browser, not here.
"""

import re
from pathlib import Path

CARDS_JS = Path(__file__).resolve().parent.parent / "docs" / "_static" / "ikp" / "cards.js"


def highlight_card_body():
    """The text of the `highlightCard` function, from its opening brace to the next function."""
    script = CARDS_JS.read_text(encoding="utf-8")
    match = re.search(r"function highlightCard\(card\)\s*\{(.*?)\n  \}\n", script, flags=re.S)
    assert match, "highlightCard not found in cards.js"
    return match.group(1)


def test_a_jump_makes_the_card_focusable_and_focuses_it_without_scrolling():
    body = highlight_card_body()
    assert re.search(r"setAttribute\(\s*'tabindex'\s*,\s*'-1'\s*\)", body)
    assert re.search(r"card\.focus\(\s*\{\s*preventScroll:\s*true\s*\}\s*\)", body)


def test_focus_comes_before_the_scroll_so_the_scroll_is_the_last_instruction():
    body = highlight_card_body()
    assert body.index("focus(") < body.index("scrollIntoView(")


def test_the_added_tabindex_is_removed_when_the_card_loses_focus():
    body = highlight_card_body()
    listener = re.search(
        r"addEventListener\(\s*'blur'\s*,\s*function\s*\(\)\s*\{(.*?)\}\s*,\s*\{\s*once:\s*true\s*\}\s*\)",
        body,
        flags=re.S,
    )
    assert listener, "no one-shot blur listener"
    assert re.search(r"removeAttribute\(\s*'tabindex'\s*\)", listener.group(1))


def test_a_jump_scrolls_instantly_when_reduced_motion_is_asked_for():
    body = highlight_card_body()
    assert re.search(r"matchMedia\(\s*'\(prefers-reduced-motion:\s*reduce\)'\s*\)", body)
    assert "'auto'" in body and "'smooth'" in body
