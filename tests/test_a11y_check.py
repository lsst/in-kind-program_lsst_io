"""Unit tests for the pure parts of scripts/a11y_check.py (no browser needed).

The script imports Playwright and axe only inside its browser function, so these
tests run in the normal test environment.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "a11y_check.py"
spec = importlib.util.spec_from_file_location("a11y_check", SCRIPT)
a11y = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a11y)


def node(owner, target="div", exempt_reason=None, fg_color="", ratio=None):
    # A node with a foreground colour gets a plausible ratio unless one is given.
    if ratio is None and fg_color:
        ratio = 4.13
    result = {
        "target": target, "html": "", "owner": owner,
        "fg_color": fg_color, "contrast_ratio": ratio,
    }
    if exempt_reason:
        result["exempt_reason"] = exempt_reason
        result["exempt_kind"] = "list"
    return result


def violation(rule_id, *nodes):
    return {"id": rule_id, "impact": "serious", "help": "help text", "nodes": list(nodes)}


def scan(*violations, incomplete=(), state="load"):
    return {
        "page": "p.html",
        "theme": "light",
        "state": state,
        "violations": list(violations),
        "incomplete": list(incomplete),
    }


OK_REFLOW = [{"page": "p.html", "state": "load", "overflow": False}]
RUN_INFO = {"axe_version": "4.99.0", "theme_version": "0.16.1", "blocked_requests": []}


# --- owner classification ---------------------------------------------------

def test_ikp_class_in_selector_is_ours():
    assert a11y.classify_owner(".ikp-filter > select", "<select>") == "ours"


def test_ikp_id_in_html_is_ours():
    assert a11y.classify_owner("div", '<div id="ikp-map" class="x">') == "ours"


def test_ikp_ancestor_makes_a_plain_element_ours():
    ancestors = '<x class="ikp-table-wrap" id="">'
    assert a11y.classify_owner("th", "<th>", ancestors) == "ours"


def test_sd_card_content_is_ours():
    target = "#ds-x > .sd-card > .sd-card-body > .sd-badge"
    assert a11y.classify_owner(target, '<span class="sd-badge">') == "ours"


def test_sd_card_ancestor_is_ours():
    assert a11y.classify_owner("span", "<span>", '<x class="sd-card-body" id="">') == "ours"


def test_other_sphinx_design_markup_is_sphinx_design():
    assert a11y.classify_owner(".sd-container-fluid", '<div class="sd-row">') == "sphinx-design"


def test_theme_chrome_is_theme():
    assert a11y.classify_owner(".bd-header a", '<a class="nav-link">') == "theme"


def test_intro_link_in_article_body_is_ours():
    ancestors = '<x class="bd-article-container" id=""> <x class="bd-article" id="">'
    assert a11y.classify_owner("p > a.reference.external", "<a>", ancestors) == "ours"


def test_sd_markup_in_article_without_ikp_or_card_is_sphinx_design():
    ancestors = '<x class="bd-article" id=""> <x class="sd-container-fluid" id="">'
    assert a11y.classify_owner("div", "<div>", ancestors) == "sphinx-design"


def test_ikp_inside_article_stays_ours():
    ancestors = '<x class="bd-article" id=""> <x class="ikp-filters" id="">'
    assert a11y.classify_owner("select", "<select>", ancestors) == "ours"


def test_prev_next_footer_and_article_container_are_theme():
    # The container and header around the article are chrome, not the article.
    ancestors = '<x class="bd-article-container" id=""> <x class="prev-next-area" id="">'
    assert a11y.classify_owner(".prev-next-title", "<p>", ancestors) == "theme"
    assert a11y.classify_owner(".bd-header-article a", "<a>", '<x class="bd-header-article" id="">') == "theme"


def test_similar_names_do_not_count_as_ikp():
    # "ikp" without the dash, or "skip-", must not be taken for our markup.
    assert a11y.classify_owner(".skip-link", '<a class="skip-link">') == "theme"


# --- exemptions ------------------------------------------------------------

EXEMPTIONS = [
    ("color-contrast", ".bd-footer", "theme footer"),
    ("label-content-name-mismatch", "theme-switch", "theme button"),
]


TEAL = "#058b8c"


def test_find_exemption_needs_rule_and_selector():
    found = a11y.find_exemption("color-contrast", "div.bd-footer a", EXEMPTIONS, TEAL)
    assert found == EXEMPTIONS[0]
    assert a11y.find_exemption("color-contrast", "div.bd-header", EXEMPTIONS, TEAL) is None
    assert a11y.find_exemption("link-name", "div.bd-footer", EXEMPTIONS) is None


def test_contrast_list_entry_also_needs_the_theme_link_colour():
    # A worse colour after a theme upgrade must not be exempted by selector alone.
    assert a11y.find_exemption("color-contrast", "div.bd-footer a", EXEMPTIONS, "#999999") is None
    assert a11y.find_exemption("color-contrast", "div.bd-footer a", EXEMPTIONS) is None
    # Other rules are matched by rule and selector only.
    assert a11y.find_exemption("label-content-name-mismatch", "x theme-switch", EXEMPTIONS)


def test_apply_exemptions_marks_theme_nodes_and_returns_stale():
    theme_node = node("theme", "div.bd-footer a", fg_color=TEAL)
    scans = [scan(violation("color-contrast", theme_node))]
    stale = a11y.apply_exemptions(scans, EXEMPTIONS)
    assert theme_node["exempt_reason"] == "theme footer"
    assert stale == [EXEMPTIONS[1]]


def test_apply_exemptions_never_exempts_our_nodes():
    ours_node = node("ours", "div.bd-footer a")
    scans = [scan(violation("color-contrast", ours_node))]
    stale = a11y.apply_exemptions(scans, EXEMPTIONS)
    assert "exempt_reason" not in ours_node
    assert stale == EXEMPTIONS


def test_empty_exemption_list_is_never_stale():
    assert a11y.apply_exemptions([scan()], []) == []


def test_shipped_exemption_entries_have_three_fields():
    for entry in a11y.EXEMPTIONS:
        assert len(entry) == 3 and all(isinstance(part, str) and part for part in entry)


def test_shipped_exemptions_match_the_theme_chrome_selectors_we_found():
    entries = a11y.EXEMPTIONS
    search = ".navbar-persistent--container > .search-button-field.search-button__button"
    navbar = ".bd-navbar-elements.navbar-nav > .active.current.nav-item > .nav-link"
    cases = [
        ("label-content-name-mismatch", search),
        ("label-content-name-mismatch", ".navbar-item > .btn-sm.theme-switch-button"),
        ("color-contrast", navbar),
        ("color-contrast", ".prev-next-info > .prev-next-title"),
        ("color-contrast", 'a[href="#"]'),
        ("color-contrast", 'a[href$="sphinx-doc.org/"]'),
        ("color-contrast", ".theme-version > a"),
    ]
    for rule_id, target in cases:
        assert a11y.find_exemption(rule_id, target, entries, TEAL), (rule_id, target)
    assert a11y.find_exemption("color-contrast", ".ikp-card a", entries, TEAL) is None


# --- node detail -----------------------------------------------------------

def test_summarize_contrast_detail_has_ratio_colours_and_size():
    axe_node = {"any": [{"message": "m", "data": {
        "contrastRatio": 4.14, "expectedContrastRatio": "4.5:1", "fgColor": "#058b8c",
        "bgColor": "#ffffff", "fontSize": "10.5pt (14px)", "fontWeight": "normal"}}]}
    detail = a11y.summarize_node_detail(axe_node)
    for part in ("4.14", "4.5:1", "#058b8c", "#ffffff", "10.5pt (14px)"):
        assert part in detail


def test_summarize_other_rules_uses_first_message():
    assert a11y.summarize_node_detail({"any": [{"message": "No name", "data": None}]}) == "No name"
    assert a11y.summarize_node_detail({}) == ""


# --- theme colour exemption --------------------------------------------------

def test_theme_colour_exempts_any_owner_for_colour_contrast_only():
    ours_node = node("ours", "a.ikp-link", fg_color="#058b8c")
    badge_node = node("ours", ".sd-badge", fg_color="#058b8c")
    other_colour = node("ours", "s.ikp-old", fg_color="#888888")
    scans = [scan(violation("color-contrast", ours_node, badge_node, other_colour))]
    a11y.apply_exemptions(scans, [])
    assert ours_node["exempt_kind"] == "theme-colour"
    assert badge_node["exempt_kind"] == "theme-colour"
    assert "exempt_kind" not in other_colour


def colour_exempt_kind(ratio):
    colour_node = node("ours", "a.ikp-link", fg_color=TEAL, ratio=ratio)
    a11y.apply_exemptions([scan(violation("color-contrast", colour_node))], [])
    return colour_node.get("exempt_kind")


def test_theme_colour_floor_is_three_to_one():
    assert a11y.THEME_COLOUR_MIN_RATIO == 3.0
    assert colour_exempt_kind(3.78) == "theme-colour"
    assert colour_exempt_kind(3.0) == "theme-colour"      # at the floor: exempt
    assert colour_exempt_kind(2.99) is None               # just below: open violation


def test_theme_colour_without_a_measured_ratio_is_not_exempt():
    colour_node = node("ours", "a.ikp-link", fg_color=TEAL)
    colour_node["contrast_ratio"] = None
    a11y.apply_exemptions([scan(violation("color-contrast", colour_node))], [])
    assert "exempt_kind" not in colour_node


def test_report_prints_the_lowest_theme_colour_ratio():
    low = node("ours", "a.low", fg_color=TEAL, ratio=3.78)
    high = node("ours", "a.high", fg_color=TEAL, ratio=4.13)
    scans = [scan(violation("color-contrast", low, high))]
    a11y.apply_exemptions(scans, [])
    text = a11y.format_report(RUN_INFO, scans, [], OK_REFLOW, 0)
    assert "exempt: theme colour: 2 (ours 2, sphinx-design 0, theme 0); lowest ratio 3.78:1" in text
    assert "(all 2 nodes exempt as the theme colour)" in text


def test_theme_colour_does_not_exempt_other_rules():
    other_rule = node("ours", "a.ikp-link", fg_color="#058b8c")
    scans = [scan(violation("link-name", other_rule))]
    a11y.apply_exemptions(scans, [])
    assert "exempt_kind" not in other_rule


def test_list_entry_is_tried_before_the_colour_rule_so_it_is_not_stale():
    theme_node = node("theme", "div.bd-footer a", fg_color="#058b8c")
    scans = [scan(violation("color-contrast", theme_node))]
    stale = a11y.apply_exemptions(scans, [EXEMPTIONS[0]])
    assert theme_node["exempt_kind"] == "list"
    assert stale == []


def test_incomplete_items_are_never_exempted():
    item_node = node("theme", "div.bd-footer a", fg_color="#058b8c")
    scans = [scan(incomplete=[violation("color-contrast", item_node)])]
    a11y.apply_exemptions(scans, EXEMPTIONS)
    assert "exempt_reason" not in item_node


def test_foreground_color_reads_axe_data_in_lower_case():
    axe_node = {"any": [{"data": {"fgColor": "#058B8C"}}]}
    assert a11y.foreground_color(axe_node) == a11y.THEME_LINK_COLOUR
    assert a11y.foreground_color({}) == ""


# --- fail-closed ownership and theme version ----------------------------------

def test_unknown_element_fails_closed_as_ours():
    # ancestor_markup=None means the browser could not find the element.
    assert a11y.classify_owner(".bd-header a", "<a>", None) == "ours"


def test_parse_theme_version():
    assert a11y.parse_theme_version("Built with the PyData Sphinx Theme 0.16.1.") == "0.16.1"
    assert a11y.parse_theme_version("") == "unknown"


# --- exit code -------------------------------------------------------------

def test_exit_code_passes_with_only_exempt_violations_and_incomplete_items():
    exempt_theme = node("theme", exempt_reason="why")
    colour = node("ours", fg_color="#058b8c")
    colour["exempt_kind"] = "theme-colour"
    scans = [scan(violation("r", exempt_theme, colour), incomplete=[violation("r", node("ours"))])]
    assert a11y.decide_exit_code(scans, [], OK_REFLOW) == 0


def test_exit_code_fails_on_open_violation_of_any_owner():
    for owner in ("ours", "sphinx-design", "theme"):
        assert a11y.decide_exit_code([scan(violation("r", node(owner)))], [], OK_REFLOW) == 1


def test_exit_code_fails_on_violation_in_the_expanded_state():
    scans = [scan(), scan(violation("r", node("ours")), state="expanded")]
    assert a11y.decide_exit_code(scans, [], OK_REFLOW) == 1


def test_exit_code_fails_on_stale_exemption():
    assert a11y.decide_exit_code([scan()], [("r", "x", "why")], OK_REFLOW) == 1


def test_exit_code_fails_on_reflow_overflow():
    assert a11y.decide_exit_code([scan()], [], [{"page": "p.html", "overflow": True}]) == 1


def test_exit_code_fails_when_the_reflow_pass_could_not_click_an_expand_button():
    reflows = [{"page": "p.html", "state": "expanded", "overflow": False, "expand_failures": 2}]
    assert a11y.decide_exit_code([scan()], [], reflows) == 1
    text = a11y.format_report(RUN_INFO, [scan()], [], reflows, 1)
    assert "2 expand button(s) could not be clicked" in text


def test_exit_code_fails_when_an_expand_button_could_not_be_clicked():
    broken = scan(state="expanded")
    broken["expand_failures"] = 1
    assert a11y.decide_exit_code([broken], [], OK_REFLOW) == 1


# --- report formatting -----------------------------------------------------

def test_report_header_has_versions_and_blocked_request_count():
    info = {**RUN_INFO, "blocked_requests": ["https://fonts.example/x.css"]}
    text = a11y.format_report(info, [scan()], [], OK_REFLOW, 0)
    assert "axe-core 4.99.0; pydata-sphinx-theme 0.16.1" in text
    assert "Blocked non-file requests: 1" in text and "fallback font" in text


def test_report_says_whether_the_expanded_scan_sorted_the_first_column():
    sorted_scan = {**scan(state="expanded"), "sorted_first_column": True}
    plain_scan = scan(state="expanded")
    assert "first column sorted: yes" in a11y.format_report(RUN_INFO, [sorted_scan], [], OK_REFLOW, 0)
    assert "first column sorted: no sortable column" in a11y.format_report(
        RUN_INFO, [plain_scan], [], OK_REFLOW, 0
    )


def test_report_shows_counts_targets_and_result():
    scans = [
        scan(
            violation("color-contrast", node("theme", "a.t"), node("ours", "span.ikp-x")),
            incomplete=[violation("aria-x", node("theme", "button.t"))],
        )
    ]
    reflows = [
        {"page": "p.html", "state": "load", "overflow": True,
         "description": "outside a table wrapper, past the window edge: table.wide (right edge 400 px)"}
    ]
    text = a11y.format_report(RUN_INFO, scans, [("r", "sel", "why")], reflows, 1)
    assert "(light mode, load state)" in text
    assert "ours=1 open, sphinx-design=0 open, theme: 0 exempt, 1 not exempt" in text
    assert "VIOLATION color-contrast (serious)" in text
    assert "NEEDS REVIEW aria-x" in text
    assert "FAIL p.html (load state): outside a table wrapper" in text
    assert "table.wide" in text
    assert "STALE: (r, 'sel') why" in text
    assert "Result: FAIL (exit 1)" in text
    assert "span.ikp-x" in text


def test_report_always_lists_every_theme_node_that_is_not_exempt():
    nodes = [node("theme", f"a.open{i}") for i in range(6)]
    text = a11y.format_report(RUN_INFO, [scan(violation("r", *nodes))], [], OK_REFLOW, 1)
    for i in range(6):
        assert f"a.open{i}" in text
    assert "theme: 0 exempt, 6 not exempt" in text


def test_report_truncates_other_nodes_and_marks_exempt_ones():
    nodes = [node("ours", f"a.n{i}") for i in range(6)]
    nodes.append(node("theme", "a.exempt", exempt_reason="known"))
    text = a11y.format_report(RUN_INFO, [scan(violation("r", *nodes))], [], OK_REFLOW, 1)
    assert "... and 4 more" in text
    assert "theme: 1 exempt, 0 not exempt" in text


def test_report_counts_theme_colour_group_separately_without_listing_nodes():
    colour = node("ours", "a.ikp-colour", fg_color="#058b8c")
    colour["exempt_kind"] = "theme-colour"
    text = a11y.format_report(RUN_INFO, [scan(violation("r", colour))], [], OK_REFLOW, 0)
    assert "exempt: theme colour: 1 (ours 1, sphinx-design 0, theme 0)" in text
    assert "a.ikp-colour" not in text
    assert "Result: PASS (exit 0)" in text


def test_report_shows_node_detail():
    detail_node = node("ours", "span.x")
    detail_node["detail"] = "contrast 3.1 (needs 4.5:1)"
    text = a11y.format_report(RUN_INFO, [scan(violation("r", detail_node))], [], OK_REFLOW, 1)
    assert "why: contrast 3.1 (needs 4.5:1)" in text


# --- main(): setup errors and stale suppression ---------------------------------

def make_site(tmp_path, pages):
    for relative in pages:
        page = tmp_path / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<html></html>")
    return tmp_path


def fake_scan(monkeypatch):
    """Replace the browser step with a clean, empty result."""
    reflows = [{"page": "p", "state": "load", "overflow": False}]
    monkeypatch.setattr(
        a11y, "run_browser_scan", lambda html_dir, pages: (RUN_INFO, [scan()], reflows)
    )


def test_main_exits_2_for_a_missing_build_directory(tmp_path, capsys):
    assert a11y.main([str(tmp_path / "nope")]) == 2
    assert "build directory not found" in capsys.readouterr().out


def test_main_exits_2_for_a_missing_page(tmp_path, capsys):
    assert a11y.main([str(tmp_path)]) == 2
    assert "not found" in capsys.readouterr().out


def test_main_exits_2_when_the_browser_step_cannot_run(tmp_path, monkeypatch, capsys):
    site = make_site(tmp_path, a11y.DEFAULT_PAGES)

    def refuse(html_dir, pages):
        raise a11y.SetupError("Chromium for Playwright is not installed.")

    monkeypatch.setattr(a11y, "run_browser_scan", refuse)
    assert a11y.main([str(site)]) == 2
    assert "ERROR: Chromium" in capsys.readouterr().out


def test_main_exits_2_for_any_other_browser_failure(tmp_path, monkeypatch, capsys):
    site = make_site(tmp_path, a11y.DEFAULT_PAGES)

    def crash(html_dir, pages):
        raise RuntimeError("navigation timed out")

    monkeypatch.setattr(a11y, "run_browser_scan", crash)
    assert a11y.main([str(site)]) == 2
    assert "ERROR: the browser scan failed: RuntimeError: navigation timed out" in capsys.readouterr().out


def test_main_reports_stale_entries_for_the_default_pages(tmp_path, monkeypatch):
    site = make_site(tmp_path, a11y.DEFAULT_PAGES)
    fake_scan(monkeypatch)
    # No scan matches any shipped entry, so they are all stale.
    assert a11y.main([str(site)]) == 1


def test_main_suppresses_stale_entries_when_a_page_subset_is_given(tmp_path, monkeypatch):
    site = make_site(tmp_path, a11y.DEFAULT_PAGES)
    fake_scan(monkeypatch)
    assert a11y.main([str(site), "--pages", a11y.DEFAULT_PAGES[0]]) == 0


def test_skipped_expand_buttons_are_reported_not_failed():
    assert a11y.skipped_expand_text(0) == ""
    assert a11y.skipped_expand_text(1) == '1 hidden "Read full description" button skipped (the text fits)'
    assert a11y.skipped_expand_text(3) == '3 hidden "Read full description" buttons skipped (the text fits)'
    # A skipped button is not a failure: the exit code ignores the count.
    skipped_only = {**scan(state="expanded"), "expand_skipped": 2, "expand_failures": 0}
    assert a11y.decide_exit_code([skipped_only], [], []) == 0
    # The report says so, so the log stays honest about what was not clicked.
    text = a11y.format_report(RUN_INFO, [skipped_only], [], OK_REFLOW, 0)
    assert a11y.skipped_expand_text(2) in text


# --- reflow decision (pure logic; the browser measurement is not tested here) ---

def reflow_measurement(**overrides):
    """A measurement of a page that fits a 320 px window; tests change one part."""
    measurement = {
        "document_scroll_width": 320, "window_width": 320,
        "container_found": True, "elements_checked": 50,
        "container_scroll_width": 320, "container_client_width": 320,
        "offenders": [],
    }
    measurement.update(overrides)
    return measurement


def test_reflow_passes_when_everything_fits():
    assert a11y.evaluate_reflow(reflow_measurement()) == (False, "")


def test_reflow_fails_when_only_the_article_container_scrolls():
    # The case the old check missed: the container absorbs the overflow, so the document stays 320 px wide.
    measurement = reflow_measurement(container_scroll_width=649)
    old_check_overflowed = measurement["document_scroll_width"] > measurement["window_width"]
    assert not old_check_overflowed
    overflow, description = a11y.evaluate_reflow(measurement)
    assert overflow
    assert "article container" in description and "649" in description


def test_reflow_fails_on_an_element_outside_a_table_wrapper():
    offender = {"tag": "select", "classes": "", "right": 448}
    overflow, description = a11y.evaluate_reflow(reflow_measurement(offenders=[offender]))
    assert overflow
    assert "select" in description and "448" in description


def test_reflow_fails_when_the_document_itself_is_wider():
    overflow, _ = a11y.evaluate_reflow(reflow_measurement(document_scroll_width=400))
    assert overflow


def test_reflow_fails_when_the_article_container_is_missing():
    measurement = reflow_measurement(
        container_found=False, container_scroll_width=None, container_client_width=None
    )
    overflow, description = a11y.evaluate_reflow(measurement)
    assert overflow
    assert "article container was not found" in description


def test_reflow_fails_when_no_elements_were_examined():
    overflow, description = a11y.evaluate_reflow(reflow_measurement(elements_checked=0))
    assert overflow
    assert "no elements were examined" in description


# Content inside .ikp-table-scroll is excluded by the in-page script, not by this helper; the browser run
# proves it (the check fails on the old CSS and passes on the new).


def test_reflow_allows_one_pixel_of_document_rounding():
    # A 1 px difference is sub-pixel rounding, not overflow.
    assert a11y.evaluate_reflow(reflow_measurement(document_scroll_width=321)) == (False, "")


def test_reflow_names_only_a_few_offenders():
    offenders = [{"tag": "span", "classes": "sd-badge", "right": 400 + n} for n in range(8)]
    _, description = a11y.evaluate_reflow(reflow_measurement(offenders=offenders))
    assert description.count("span.sd-badge") == a11y.MAX_REPORTED_OFFENDERS
    assert "and 3 more" in description
