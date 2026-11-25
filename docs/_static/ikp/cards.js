/*
 * cards.js: shared behaviour for the card pages of the In-Kind Program site
 * (Telescope Access, Datasets and Software): filters, search, sorting,
 * jump-to-card highlighting, links to hidden cards and the "Show more" buttons.
 *
 * Sphinx adds this file to every page of the site (see conf.py), so it must do
 * nothing on a page that has no cards. Each page's setup below runs only when
 * that page's own table is present. The Computing Resources (IDAC) page has no
 * such table and keeps its own inline script.
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
 * empty so nothing is announced at load. `announce` puts text in it: at once
 * after a drop-down change, a reset or a `pageshow`, but only after a pause of
 * half a second while the visitor types, so a reader is not interrupted at every
 * key. It sets the text only when it differs from the last announcement, so a
 * `pageshow` re-apply that changes nothing stays silent. A sort uses the same
 * `announce` ("Sorted by Status, ascending") at once.
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
  // count" above), the pause before a delayed announcement, and the text last
  // announced. `lastAnnounced` starts as the visible count line's text (see
  // `setupFiltering`), so the first, unchanged count is not announced.
  var ANNOUNCE_DELAY_MS = 500;
  var announcer = { region: null, timer: null, lastAnnounced: '' };

  // Tell screen readers `text` through the status region. Pass
  // `{delay: true}` to wait for a pause of ANNOUNCE_DELAY_MS first (each call
  // restarts the wait); without it the text is set at once. Text equal to the
  // last announcement is skipped, because setting identical text makes no
  // announcement anyway. Does nothing on a page without the region.
  function announce(text, options) {
    announcer.region = announcer.region || document.querySelector('.ikp-status');
    if (!announcer.region) { return; }
    clearTimeout(announcer.timer);
    announcer.timer = null;
    function write() {
      if (text === announcer.lastAnnounced) { return; }
      announcer.lastAnnounced = text;
      announcer.region.textContent = text;
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
    if (countElement) { announcer.lastAnnounced = countElement.textContent; }

    // Rewrite the visible count line at once from the current `visibleCount`, and
    // announce the same text (after a typing pause if `options.delay` is true).
    function updateResultCount(announceOptions) {
      if (!countElement) { return; }
      var text = (visibleCount === 0)
        ? options.noneText
        : 'Showing ' + visibleCount + ' of ' + rows.length + ' ' + options.noun;
      if (countElement.textContent !== text) { countElement.textContent = text; }
      announce(text, announceOptions);
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

  // Scroll a card into view and outline it for a moment.
  function highlightCard(card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    outlineCard(card);
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
  // also answers Enter and Space), and each column's name is read once, before
  // any arrow exists, for the announcement.
  // Returns {sortBy, getSortState}.
  function wireTableSorting(table) {
    var sortState = { header: null, ascending: true };
    var headers = Array.prototype.slice.call(table.querySelectorAll('th[data-sort]'));

    // Each column's name for the announcement. Read now, while the button holds
    // only the name (the arrow is empty until a sort is made).
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

  // Make each "Show more" button (matched by `buttonSelector`) toggle the
  // `ikp-expanded` class on the element just before it, and swap its own label
  // between the `data-expand-label` and `data-collapse-label` texts.
  function wireExpandButtons(buttonSelector) {
    document.querySelectorAll(buttonSelector).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var target = btn.previousElementSibling;
        var expanded = target.classList.toggle('ikp-expanded');
        btn.textContent = expanded
          ? btn.getAttribute('data-collapse-label')
          : btn.getAttribute('data-expand-label');
      });
    });
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
    wireExpandButtons('.ikp-expand-btn');
    wireTableSorting(table);
    keepListInSync(filtering);
    wireHiddenCardLinks(filtering);
    wireTeaserLinks();
  }

  // -------------------------------------------------------------------------
  // 5. Start-up
  // -------------------------------------------------------------------------

  // Each card page is recognised by its table. A page without one (every other
  // page of the site) is left alone.
  function init() {
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
