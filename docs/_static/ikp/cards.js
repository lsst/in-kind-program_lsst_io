/*
 * cards.js: shared behaviour for the card pages of the In-Kind Program site
 * (Telescope Access, Datasets and Software): filters, search, sorting,
 * jump-to-card highlighting and the "Show more" buttons.
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
    var anchor = document.getElementById(item.getAttribute('data-card'));
    return anchor ? anchor.closest('.sd-col') : null;
  }

  // Wire up the filtering of one page: its drop-downs (every
  // `select[data-filter-key]`), its search box and its rows, cards and map
  // markers.
  //
  // options.table              the page's table
  // options.searchInput        the search box, or null
  // options.extraRequirements  optional function returning more required tokens
  //                            as [{key, value}], for a control that is not a
  //                            drop-down (the Datasets "available only" button)
  //
  // Returns {applyFilters, getVisibleCount}: the page can re-apply filters after
  // a change of its own, and read how many rows pass the filters now.
  function setupFiltering(options) {
    var searchIndex = readSearchIndex();
    var selects = Array.prototype.slice.call(document.querySelectorAll('select[data-filter-key]'));
    var rows = Array.prototype.slice.call(options.table.querySelectorAll('.ikp-row'));
    var markers = Array.prototype.slice.call(document.querySelectorAll('.ikp-map-marker'));

    // How many rows pass the filters. Every row is shown at the start. The count
    // is kept up to date for a result count, which reads it through
    // `getVisibleCount`.
    var visibleCount = rows.length;

    // The tokens an item must have: one per drop-down that is not on "All".
    function requiredTokens() {
      var required = [];
      selects.forEach(function (select) {
        if (select.value) { required.push({ key: select.getAttribute('data-filter-key'), value: select.value }); }
      });
      return required.concat(options.extraRequirements ? options.extraRequirements() : []);
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

    function applyFilters() {
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

    selects.forEach(function (select) { select.addEventListener('change', applyFilters); });
    if (options.searchInput) { options.searchInput.addEventListener('input', applyFilters); }

    return {
      applyFilters: applyFilters,
      getVisibleCount: function () { return visibleCount; }
    };
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

  // Scroll a card into view and outline it for a moment.
  function highlightCard(card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    card.classList.add('ikp-highlight');
    setTimeout(function () { card.classList.remove('ikp-highlight'); }, 1500);
  }

  // Make the headers of `table` (those with a `data-sort` attribute) sort the
  // rows when clicked: the first click on a header sorts ascending, and each
  // further click on the same header reverses the direction. Clicking another
  // header starts that header ascending. The rows are compared by their
  // `data-<key>` attribute.
  //
  // The sort state (which header was clicked last, and which direction) is kept
  // in one place, for an aria-sort indicator to read.
  // Returns {sortBy, getSortState}.
  function wireTableSorting(table) {
    var sortState = { header: null, ascending: true };

    // Sort the rows by one column header, updating the sort state.
    function sortBy(th) {
      sortState.ascending = (sortState.header === th) ? !sortState.ascending : true;
      sortState.header = th;
      var key = th.getAttribute('data-sort');
      var ascending = sortState.ascending;
      var tbody = table.querySelector('tbody');
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
      rows.sort(function (a, b) {
        var av = a.getAttribute('data-' + key) || '';
        var bv = b.getAttribute('data-' + key) || '';
        return ascending ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      rows.forEach(function (r) { tbody.appendChild(r); });
    }

    table.querySelectorAll('th[data-sort]').forEach(function (th) {
      th.addEventListener('click', function () { sortBy(th); });
    });

    return {
      sortBy: sortBy,
      // A copy, so callers cannot change the state by accident.
      getSortState: function () { return { header: sortState.header, ascending: sortState.ascending }; }
    };
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
    setupFiltering({ table: table, searchInput: document.getElementById('ikt-search') });
    wireCardJumps(table);
    wireTableSorting(table);
  }

  // -------------------------------------------------------------------------
  // 3. Datasets page
  // -------------------------------------------------------------------------
  function initDatasets(table) {
    var showAvailableOnly = false;

    // The "available only" button asks for one more token, under the `status`
    // key (the page has no status drop-down).
    var filtering = setupFiltering({
      table: table,
      searchInput: document.getElementById('ikc-search'),
      extraRequirements: function () {
        return showAvailableOnly ? [{ key: 'status', value: 'status-available' }] : [];
      }
    });

    var toggleBtn = document.getElementById('ikc-toggle-status');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        showAvailableOnly = !showAvailableOnly;
        toggleBtn.setAttribute('aria-pressed', showAvailableOnly ? 'true' : 'false');
        toggleBtn.textContent = showAvailableOnly ? 'Include future datasets' : 'Show available only';
        filtering.applyFilters();
      });
    }

    wireCardJumps(table);
    wireExpandButtons('.ikp-more-btn');
    wireTableSorting(table);
  }

  // -------------------------------------------------------------------------
  // 4. Software page
  // -------------------------------------------------------------------------
  function initSoftware(table) {
    setupFiltering({ table: table, searchInput: document.getElementById('ikc-sw-search') });
    wireCardJumps(table);
    wireExpandButtons('.ikp-expand-btn');
    wireTableSorting(table);
  }

  // -------------------------------------------------------------------------
  // 5. Start-up
  // -------------------------------------------------------------------------

  // Each card page is recognised by its table. A page without one (every other
  // page of the site) is left alone.
  function init() {
    var telescopesTable = document.getElementById('ikt-telescopes-table');
    if (telescopesTable) { initTelescopes(telescopesTable); }
    var datasetsTable = document.getElementById('ikc-datasets-table');
    if (datasetsTable) { initDatasets(datasetsTable); }
    var softwareTable = document.getElementById('ikc-sw-table');
    if (softwareTable) { initSoftware(softwareTable); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
