/*
 * cards.js: shared behaviour for the card pages of the In-Kind Program site
 * (Telescope Access, Datasets and Software): filters, search, sorting,
 * jump-to-card highlighting (the card also takes keyboard focus), links to
 * hidden cards, the "Show more" buttons and card titles as headings.
 *
 * Sphinx adds this file to every page of the site (see conf.py), so it must do
 * nothing on a page that has none of our cards. Each page's setup below runs
 * only when that page's own table is present. The one step that runs on every
 * page is marking card titles as headings, and it only matches titles inside
 * our own `.ikp-card` cards. The Computing Resources (IDAC) page has no such
 * table or cards and keeps its own inline script.
 *
 * Timing: the file is loaded with `defer`, and `init` also waits for
 * DOMContentLoaded if the page is still loading. The card grid comes after the
 * table in the page source, so setup waits until the whole page is parsed.
 *
 * How filtering works: the table rows and map markers carry the filter data.
 * Each carries one `data-filter-<key>` attribute per filter (a space-separated
 * list of tokens) and `data-card`, the id of its card. Each filter drop-down
 * names its key once, in `data-filter-key`. A row or marker passes when it has,
 * as a whole token, the value chosen in every drop-down, and its search text
 * contains the search box text. A card is shown or hidden together with its row
 * (it is found by `data-card`), so cards carry no filter data and no class
 * names are matched.
 *
 * Back and forward: the Back and Forward buttons make the browser restore the
 * drop-down and search values the visitor had, and it does so after the
 * scripts have run. Each page therefore applies its filters when it sets up and
 * again on every `pageshow` event, so the list always matches the restored
 * controls (see `keepListInSync`).
 *
 * Links to a hidden card: a same-page "Also see" link, or a link in the
 * "Highlighted" teaser row, to a card that the filters or search hide clears
 * them first, so the card shows (see `wireHiddenCardLinks`). A `#card` in the
 * address never clears them. A teaser link also outlines its card, as a table
 * title does (see `wireTeaserLinks`). The teaser row is not a row or a card, so
 * the filters never touch it.
 *
 * Result count: each page has a visible line, `<p class="ikp-result-count">`,
 * rendered by the template with the full count ("Showing N of N ..."). After
 * every change the script rewrites it at once ("Showing 3 of 15 facilities", or
 * the page's "No ... match the filters" text), so it always matches the list.
 * Screen readers are told through a separate, visually hidden status region
 * (`<p class="ikp-visually-hidden ikp-status" role="status">`), which starts
 * empty so nothing is announced at load. `announceCount` puts the count in it:
 * at once after a drop-down change, a reset or a `pageshow`, but only after a
 * pause of half a second while the visitor types, so a reader is not
 * interrupted at every key. A count equal to the last count announced is
 * skipped, so a `pageshow` re-apply that changes nothing stays silent. A sort
 * is announced separately ("Sorted by Status, ascending"): `announce` writes it
 * at once, and it neither delays nor disturbs the count announcement.
 *
 * Sorting: each sortable header holds a button, so the keyboard can reach it.
 * The sorted column's header carries `aria-sort` and an arrow (hidden from
 * screen readers, which get `aria-sort` and the announcement); no header has
 * either until a sort is made.
 *
 * Class hooks: `ikp-row` and `ikp-map-marker` are used only by this script and
 * have no CSS rules, so do not remove them as unused.
 *
 * Data from the build: each page embeds its search text as a JSON block
 * (`<script type="application/json" data-ikp="search-index">`), read by
 * `readSearchIndex` below. No page data lives in this file.
 *
 * Layout of this file:
 *   1. Helpers shared by the pages (filtering, card jumps, sorting, "Show more")
 *   2. Telescope Access page
 *   3. Datasets page
 *   4. Software page
 *   5. Start-up
 */
(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // 1. Helpers shared by the pages
  // -------------------------------------------------------------------------

  // Read the page's search text from its embedded JSON block. The result maps
  // a card's anchor id (the `data-card` of its table row and map
  // marker) to lower-case text to search in.
  function readSearchIndex() {
    var block = document.querySelector('script[type="application/json"][data-ikp="search-index"]');
    return block ? JSON.parse(block.textContent) : {};
  }

  // The hidden status region that screen readers announce from (see "Result
  // count" above), the pause before a delayed count announcement, and the count
  // text last announced. `lastCount` starts as the visible count line's text
  // (see `setupFiltering`), so the first, unchanged count is not announced.
  var ANNOUNCE_DELAY_MS = 500;
  var announcer = { region: null, timer: null, lastCount: '' };

  // Put `text` in the status region at once. Does nothing without the region.
  // A sort message needs no duplicate check: two sort messages in a row always
  // differ (the same header flips direction; another header changes the name).
  function announce(text) {
    announcer.region = announcer.region || document.querySelector('.ikp-status');
    if (announcer.region) { announcer.region.textContent = text; }
  }

  // Announce the result count. A count equal to the last one announced is
  // skipped, so a re-apply that changes nothing stays silent, whatever other
  // message (a sort) was announced in between. `{delay: true}` waits for a
  // typing pause first; each call restarts the wait.
  function announceCount(text, options) {
    clearTimeout(announcer.timer);
    announcer.timer = null;
    function write() {
      if (text === announcer.lastCount) { return; }
      announcer.lastCount = text;
      announce(text);
    }
    if (options && options.delay) {
      announcer.timer = setTimeout(write, ANNOUNCE_DELAY_MS);
    } else {
      write();
    }
  }

  // Show or hide an element.
  function setVisible(el, visible) {
    // sphinx-design's grid-item wrapper carries a `display: flex !important`
    // class (.sd-d-flex-row), which beats a plain inline `style="display:none"`.
    // Setting the inline override with !important priority is the only thing
    // that reliably wins.
    if (visible) {
      el.style.removeProperty('display');
    } else {
      el.style.setProperty('display', 'none', 'important');
    }
  }

  // True if the row or marker `item` has `value` as a whole token in its
  // `data-filter-<key>` attribute (a space-separated list; a part of a token
  // does not count).
  function hasToken(item, key, value) {
    var tokens = (item.getAttribute('data-filter-' + key) || '').split(/\s+/);
    return tokens.indexOf(value) !== -1;
  }

  // The card for a table row or map marker: the grid item (sphinx-design's
  // `sd-col` wrapper) around the element whose id is the item's `data-card`.
  // Returns null if there is no such card.
  function cardOf(item) {
    return cardById(item.getAttribute('data-card'));
  }

  // The card whose anchor has this id: the grid item around that element.
  // Returns null if there is no such card.
  function cardById(id) {
    var anchor = document.getElementById(id);
    return anchor ? anchor.closest('.sd-col') : null;
  }

  // Wire up the filtering of one page: its drop-downs (every
  // `select[data-filter-key]`), its search box and its rows, cards and map
  // markers.
  //
  // options.table        the page's table
  // options.searchInput  the search box, or null
  // options.noun         the plural noun for the count line ("facilities")
  // options.noneText     the count line when no row passes ("No facilities match the filters")
  //
  // Returns {applyFilters, resetFilters, getVisibleCount}: the page can
  // re-apply filters after a change of its own, clear them all, and read how
  // many rows pass the filters now.
  function setupFiltering(options) {
    var searchIndex = readSearchIndex();
    var selects = Array.prototype.slice.call(document.querySelectorAll('select[data-filter-key]'));
    var rows = Array.prototype.slice.call(options.table.querySelectorAll('.ikp-row'));
    var markers = Array.prototype.slice.call(document.querySelectorAll('.ikp-map-marker'));

    // How many rows pass the filters. Every row is shown at the start. The count
    // is kept up to date for the result count line, and the page can read it
    // through `getVisibleCount`.
    var visibleCount = rows.length;

    // The visible result count line. Its rendered text (the full count) counts
    // as already known, so only a change from it is announced.
    var countElement = document.querySelector('.ikp-result-count');
    if (countElement) { announcer.lastCount = countElement.textContent; }

    // Rewrite the visible count line at once from the current `visibleCount`, and
    // announce the same text (after a typing pause if `options.delay` is true).
    function updateResultCount(announceOptions) {
      if (!countElement) { return; }
      var text = (visibleCount === 0)
        ? options.noneText
        : 'Showing ' + visibleCount + ' of ' + rows.length + ' ' + options.noun;
      if (countElement.textContent !== text) { countElement.textContent = text; }
      announceCount(text, announceOptions);
    }

    // The tokens an item must have: one per drop-down that is not on "All".
    function requiredTokens() {
      var required = [];
      selects.forEach(function (select) {
        if (select.value) { required.push({ key: select.getAttribute('data-filter-key'), value: select.value }); }
      });
      return required;
    }

    // True if the item has every required token and matches the search text.
    // The search index is keyed by card id, which is also the item's `data-card`.
    function itemMatches(item, required, query) {
      var hasAll = required.every(function (r) { return hasToken(item, r.key, r.value); });
      if (!hasAll) { return false; }
      if (!query) { return true; }
      var text = searchIndex[item.getAttribute('data-card')] || '';
      return text.indexOf(query) !== -1;
    }

    // Show or hide the rows, cards and markers. Leaves the count line alone.
    function filterRows() {
      var required = requiredTokens();
      var query = options.searchInput ? options.searchInput.value.trim().toLowerCase() : '';
      visibleCount = 0;
      rows.forEach(function (row) {
        var show = itemMatches(row, required, query);
        if (show) { visibleCount += 1; }
        setVisible(row, show);
        // A card follows its row.
        var card = cardOf(row);
        if (card) { setVisible(card, show); }
      });
      markers.forEach(function (marker) {
        setVisible(marker, itemMatches(marker, required, query));
      });
    }

    // Filter, and update the count line and its announcement at once.
    function applyFilters() {
      filterRows();
      updateResultCount();
    }

    selects.forEach(function (select) { select.addEventListener('change', applyFilters); });
    // Typing filters and updates the visible count at once, but the
    // announcement waits for a pause.
    if (options.searchInput) {
      options.searchInput.addEventListener('input', function () {
        filterRows();
        updateResultCount({ delay: true });
      });
    }

    // Put every drop-down back on "All", empty the search box and show
    // everything again.
    function resetFilters() {
      selects.forEach(function (select) { select.value = ''; });
      if (options.searchInput) { options.searchInput.value = ''; }
      applyFilters();
    }

    return {
      applyFilters: applyFilters,
      resetFilters: resetFilters,
      getVisibleCount: function () { return visibleCount; }
    };
  }

  // Keep a page's list in step with its controls: apply the filters now, and
  // again on every `pageshow`. The browser restores form values after Back or
  // Forward only after the scripts have run, so the values read at setup can be
  // the defaults. (`pageshow` fires after a normal load too, and when the page
  // comes back from the browser's cache.) `filtering` is the object returned
  // by `setupFiltering`.
  function keepListInSync(filtering) {
    filtering.applyFilters();
    window.addEventListener('pageshow', function () { filtering.applyFilters(); });
  }

  // Clicking a title link in `table`, or a map marker, scrolls to that row's
  // (or marker's) card and highlights it.
  function wireCardJumps(table) {
    function jump(item) {
      var card = cardOf(item);
      if (card) { highlightCard(card); }
    }
    table.querySelectorAll('.ikp-title-link').forEach(function (link) {
      link.addEventListener('click', function () { jump(link.closest('tr')); });
    });
    document.querySelectorAll('.ikp-map-marker').forEach(function (marker) {
      marker.addEventListener('click', function () { jump(marker); });
    });
  }

  // Outline a card for a moment.
  function outlineCard(card) {
    card.classList.add('ikp-highlight');
    setTimeout(function () { card.classList.remove('ikp-highlight'); }, 1500);
  }

  // Move keyboard focus to a card, outline it for a moment, and scroll it into
  // view.
  //
  // Focus moves because a screen reader follows focus: its position moves with
  // it to the card the visitor jumped to, and the next Tab goes into that card
  // instead of starting again from the table. The card (the grid item that gets
  // the outline) is not focusable by default, so it gets `tabindex="-1"`
  // (focusable by script, not part of the Tab order) at the moment of the jump,
  // not at page load. If the script added it, it removes it again when the card
  // loses focus: a card that kept the attribute would take focus on later
  // clicks inside it and on later `#card` jumps, unlike the other cards.
  //
  // Focus comes first, with `preventScroll`, and `scrollIntoView` comes last, so
  // the smooth scroll is always the final scroll instruction, even in a browser
  // that ignores `preventScroll`.
  //
  // Browsers generally draw the focus ring only after keyboard use, so a mouse
  // jump usually shows none. The theme's ring shows around the card for a
  // keyboard user, which is kept by choice.
  //
  // The scroll is instant when the visitor has asked for reduced motion:
  // 'auto' follows the page's CSS, which the theme makes instant for them. The
  // setting is read at each jump, not at page load, so a change applies at once.
  function highlightCard(card) {
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!card.hasAttribute('tabindex')) {
      card.setAttribute('tabindex', '-1');
      card.addEventListener('blur', function () {
        card.removeAttribute('tabindex');
      }, { once: true });
    }
    card.focus({ preventScroll: true });
    outlineCard(card);
    card.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }

  // True for a click that opens a new tab or window (a modifier key or a
  // non-primary button): the card on this page is not the one that opens.
  function opensElsewhere(event) {
    return event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0;
  }

  // Make a same-page "Also see" or teaser link to a card that the filters or
  // search are hiding still work. When the link is clicked, the filters and
  // search are cleared first (before the browser follows the link), so the card
  // shows and the browser scrolls to it. A link to another page is left alone,
  // and so is a click that opens a new tab or window: that page starts with no
  // filters. `filtering` is the object returned by `setupFiltering`.
  function wireHiddenCardLinks(filtering) {
    document.querySelectorAll('.ikp-also-see, .ikp-teaser-link').forEach(function (link) {
      link.addEventListener('click', function (event) {
        if (opensElsewhere(event) || link.pathname !== window.location.pathname) { return; }
        // Card ids are plain ASCII, so the hash is used as it is.
        var card = cardById(link.hash.slice(1));
        if (card && card.style.display === 'none') { filtering.resetFilters(); }
      });
    });
  }

  // A click on a link in the "Highlighted" teaser row outlines the card it
  // names, like a click on a table title. It does not scroll: the link's own
  // jump to its `#card` does that, and also updates the address and where
  // keyboard focus starts. A click that opens a new tab or window is left alone.
  // Call this after `wireHiddenCardLinks`, so the card is shown first.
  function wireTeaserLinks() {
    document.querySelectorAll('.ikp-teaser-link').forEach(function (link) {
      link.addEventListener('click', function (event) {
        if (opensElsewhere(event)) { return; }
        var card = cardById(link.hash.slice(1));
        if (card) { outlineCard(card); }
      });
    });
  }

  // Make the headers of `table` (those with a `data-sort` attribute) sort the
  // rows when clicked: the first click on a header sorts ascending, and each
  // further click on the same header reverses the direction. Clicking another
  // header starts that header ascending. The rows are compared by their
  // `data-<key>` attribute, as text; a header with `data-sort-type="number"`
  // compares the attribute as a number instead, and rows with no number come
  // last in either direction.
  //
  // The sort state (which header was clicked last, and which direction) is kept
  // in one place. It drives the `aria-sort` attribute and arrow on the headers.
  // The click listener is on the button inside each header (a native button
  // also answers Enter and Space).
  // Returns {sortBy, getSortState}.
  function wireTableSorting(table) {
    var sortState = { header: null, ascending: true };
    var headers = Array.prototype.slice.call(table.querySelectorAll('th[data-sort]'));

    // Each column's name for the announcement. Read once, now, while the button
    // holds only the name (the arrow is empty until a sort is made). The
    // template gives every sortable header a button; a test checks it.
    var columnNames = new Map();
    headers.forEach(function (th) {
      columnNames.set(th, th.querySelector('button').textContent.trim());
    });

    // Show the sort state: clear `aria-sort` and the arrow from every header of
    // this table, then mark the sorted one. The arrow is a visual cue only; the
    // `aria-sort` attribute and the announcement carry the same information.
    function showSortState(sortedHeader, ascending) {
      headers.forEach(function (th) {
        th.removeAttribute('aria-sort');
        th.querySelector('.ikp-sort-arrow').textContent = '';
      });
      sortedHeader.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
      sortedHeader.querySelector('.ikp-sort-arrow').textContent = ascending ? '\u25B2' : '\u25BC';
    }

    // Sort the rows by one column header, updating the sort state.
    function sortBy(th) {
      sortState.ascending = (sortState.header === th) ? !sortState.ascending : true;
      sortState.header = th;
      var key = th.getAttribute('data-sort');
      var isNumber = th.getAttribute('data-sort-type') === 'number';
      var ascending = sortState.ascending;
      var tbody = table.querySelector('tbody');
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
      rows.sort(function (a, b) {
        var av = a.getAttribute('data-' + key) || '';
        var bv = b.getAttribute('data-' + key) || '';
        if (isNumber) { return compareNumbers(av, bv, ascending); }
        return ascending ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      rows.forEach(function (r) { tbody.appendChild(r); });

      showSortState(th, ascending);
      // VoiceOver does not reliably announce an `aria-sort` change, so say it.
      announce('Sorted by ' + columnNames.get(th) + ', ' + (ascending ? 'ascending' : 'descending'));
    }

    headers.forEach(function (th) {
      th.querySelector('button').addEventListener('click', function () { sortBy(th); });
    });

    return {
      sortBy: sortBy,
      // A copy, so callers cannot change the state by accident.
      getSortState: function () { return { header: sortState.header, ascending: sortState.ascending }; }
    };
  }

  // Compare two attribute values as numbers. A blank (or unreadable) value goes
  // after every number whichever way the column is sorted, so a row with no
  // value never ends up at the top.
  function compareNumbers(a, b, ascending) {
    var an = parseFloat(a);
    var bn = parseFloat(b);
    var aBlank = isNaN(an);
    var bBlank = isNaN(bn);
    if (aBlank || bBlank) { return (aBlank ? 1 : 0) - (bBlank ? 1 : 0); }
    return ascending ? an - bn : bn - an;
  }

  // The glyphs shown after a toggle button's label. They sit in an
  // `aria-hidden` span, so a screen reader announces the label only.
  var GLYPH_DOWN = '\u25BE';
  var GLYPH_UP = '\u25B4';

  // Set a toggle button's content to its label, a space and the glyph. The
  // content is built with DOM methods so the label is always handled as text.
  function setToggleContent(btn, label, glyph) {
    var glyphSpan = document.createElement('span');
    glyphSpan.setAttribute('aria-hidden', 'true');
    glyphSpan.textContent = glyph;
    btn.textContent = '';
    btn.appendChild(document.createTextNode(label + ' '));
    btn.appendChild(glyphSpan);
  }

  // The region a toggle button opens and closes: the element named by its
  // `aria-controls`.
  function regionFor(btn) {
    return document.getElementById(btn.getAttribute('aria-controls'));
  }

  // Make each "Show more" button (matched by `buttonSelector`) toggle the
  // `ikp-expanded` class on the region it controls, keep its own
  // `aria-expanded` in step, and swap its label between the `data-expand-label`
  // and `data-collapse-label` texts.
  //
  // `afterToggle` is optional. When given, it is called after each click with
  // the button, the region and the new expanded state, once the class,
  // `aria-expanded` and label are updated.
  function wireExpandButtons(buttonSelector, afterToggle) {
    document.querySelectorAll(buttonSelector).forEach(function (btn) {
      var region = regionFor(btn);
      if (!region) { return; }
      btn.addEventListener('click', function () {
        var expanded = region.classList.toggle('ikp-expanded');
        btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        setToggleContent(btn,
          btn.getAttribute(expanded ? 'data-collapse-label' : 'data-expand-label'),
          expanded ? GLYPH_UP : GLYPH_DOWN);
        if (afterToggle) { afterToggle(btn, region, expanded); }
      });
    });
  }

  // Datasets: the extra fields are always there to open, so each region becomes
  // collapsible (the CSS hides it) and its button is shown. Without this script
  // the fields stay visible and the buttons stay hidden.
  function enableDatasetToggles() {
    document.querySelectorAll('.ikp-more-btn').forEach(function (btn) {
      var region = regionFor(btn);
      if (!region) { return; }
      region.classList.add('ikp-collapsible');
      btn.hidden = false;
    });
  }

  // Software: clamp a description to three lines, and show its button and the
  // fade only if the text is longer than that. A short description is left
  // whole, with neither.
  function measureDescription(region, btn) {
    // Never re-measure an open description: its text is not clamped, so it
    // cannot show whether it overflows. Its button stays shown.
    if (region.classList.contains('ikp-expanded')) { return; }
    // The clamp stays on whenever the description is collapsed. Only the fade
    // and the button change, so measuring never alters the size being measured.
    region.classList.add('ikp-collapsible');
    // A card hidden by a filter has no box to measure. The size observer runs
    // again when a filter shows it.
    if (region.getClientRects().length === 0) { return; }
    var overflows = region.scrollHeight > region.clientHeight + 1;
    region.classList.toggle('ikp-faded', overflows);
    // Hiding a button that has focus (on a resize, or when the description
    // collapses) is accepted: focus falls to the body, and the next Tab goes to
    // the next control in the same card, so the keyboard position is kept.
    btn.hidden = !overflows;
  }

  // Software: pair each button with its description, and measure the
  // descriptions at load, after the fonts load, and on size changes.
  function enableDescriptionToggles() {
    var pairs = [];
    // The same pairs, found by the id of the description (for the size observer).
    var pairByRegionId = {};
    document.querySelectorAll('.ikp-expand-btn').forEach(function (btn) {
      var region = regionFor(btn);
      if (!region) { return; }
      var pair = { region: region, btn: btn };
      pairs.push(pair);
      pairByRegionId[region.id] = pair;
    });

    function measureAll() {
      pairs.forEach(function (pair) { measureDescription(pair.region, pair.btn); });
    }

    // Measure as soon as the script runs, so a long description is clamped as
    // early as possible.
    measureAll();

    // The text can wrap differently once the web fonts arrive.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(measureAll);
    }

    // Measure again when a description changes size: a resized window, or a
    // card that a filter has just shown. Browsers without ResizeObserver fall
    // back to a debounced window resize.
    if (typeof ResizeObserver === 'function') {
      var observer = new ResizeObserver(function (entries) {
        entries.forEach(function (entry) {
          var pair = pairByRegionId[entry.target.id];
          if (pair) { measureDescription(pair.region, pair.btn); }
        });
      });
      pairs.forEach(function (pair) { observer.observe(pair.region); });
    } else {
      var timer = null;
      window.addEventListener('resize', function () {
        clearTimeout(timer);
        timer = setTimeout(measureAll, 150);
      });
    }

    // Measure again when a stylesheet is added or removed. A text-spacing
    // stylesheet (from a bookmarklet or an extension) changes how the text wraps
    // without changing the size of the clamp box, so the size observer above
    // does not notice, and a fourth line could be left with no button to reach it.
    // Only the children of <head> and <html> are watched, not the whole page, so
    // this stays cheap. Limits: a stylesheet appended to <body> is not seen, and
    // a style change that adds no element (CSS injected by the browser itself, or
    // a style attribute) is not caught. A window resize still measures again.
    if (typeof MutationObserver === 'function') {
      var styleTimer = null;
      var isStylesheet = function (node) {
        if (node.nodeName === 'STYLE') { return true; }
        return node.nodeName === 'LINK' && /stylesheet/i.test(node.getAttribute('rel') || '');
      };
      var styleObserver = new MutationObserver(function (mutations) {
        var changed = mutations.some(function (mutation) {
          return Array.prototype.some.call(mutation.addedNodes, isStylesheet) ||
            Array.prototype.some.call(mutation.removedNodes, isStylesheet);
        });
        if (!changed) { return; }
        // Wait for the stylesheet to apply, and for several to settle into one pass.
        clearTimeout(styleTimer);
        styleTimer = setTimeout(measureAll, 150);
      });
      styleObserver.observe(document.head, { childList: true });
      styleObserver.observe(document.documentElement, { childList: true });
    }
  }

  // -------------------------------------------------------------------------
  // 2. Telescope Access page
  // -------------------------------------------------------------------------
  function initTelescopes(table) {
    var filtering = setupFiltering({ table: table, searchInput: document.getElementById('ikp-search'),
      noun: 'facilities', noneText: 'No facilities match the filters' });
    wireCardJumps(table);
    wireTableSorting(table);
    keepListInSync(filtering);
    wireHiddenCardLinks(filtering);
  }

  // -------------------------------------------------------------------------
  // 3. Datasets page
  // -------------------------------------------------------------------------
  function initDatasets(table) {
    var filtering = setupFiltering({ table: table, searchInput: document.getElementById('ikp-search'),
      noun: 'datasets', noneText: 'No datasets match the filters' });
    wireCardJumps(table);
    enableDatasetToggles();
    wireExpandButtons('.ikp-more-btn');
    wireTableSorting(table);
    keepListInSync(filtering);
    wireHiddenCardLinks(filtering);
    wireTeaserLinks();
  }

  // -------------------------------------------------------------------------
  // 4. Software page
  // -------------------------------------------------------------------------
  function initSoftware(table) {
    var filtering = setupFiltering({ table: table, searchInput: document.getElementById('ikp-sw-search'),
      noun: 'software contributions', noneText: 'No software contributions match the filters' });
    wireCardJumps(table);
    enableDescriptionToggles();
    // A description that collapses may already fit in three lines, so its size
    // does not change and the size observer stays silent. Measure it again here.
    wireExpandButtons('.ikp-expand-btn', function (btn, region, expanded) {
      if (!expanded) { measureDescription(region, btn); }
    });
    wireTableSorting(table);
    keepListInSync(filtering);
    wireHiddenCardLinks(filtering);
    wireTeaserLinks();
  }

  // Make each card's title a level-2 heading, so a screen-reader user can jump
  // from card to card. sphinx-design writes the title as a <div>, and the page
  // source gives us no way to change that, so it is done here. Only titles inside
  // our own `.ikp-card` cards are touched: this file loads on every page, and the
  // cards on other pages (such as the IDAC resources page) must stay as they are.
  // It does not depend on the filters, and running it twice changes nothing.
  // Without JavaScript the titles stay plain text.
  function markCardTitlesAsHeadings() {
    document.querySelectorAll('.ikp-card .sd-card-title').forEach(function (title) {
      title.setAttribute('role', 'heading');
      title.setAttribute('aria-level', '2');
    });
  }

  // -------------------------------------------------------------------------
  // 5. Start-up
  // -------------------------------------------------------------------------

  // Each card page is recognised by its table. A page without one (every other
  // page of the site) is left alone, apart from the heading step, which only
  // matches titles inside `.ikp-card` cards and so changes nothing there.
  function init() {
    markCardTitlesAsHeadings();
    var telescopesTable = document.getElementById('ikp-telescopes-table');
    if (telescopesTable) { initTelescopes(telescopesTable); }
    var datasetsTable = document.getElementById('ikp-datasets-table');
    if (datasetsTable) { initDatasets(datasetsTable); }
    var softwareTable = document.getElementById('ikp-sw-table');
    if (softwareTable) { initSoftware(softwareTable); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
