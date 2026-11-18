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
 * Class hooks: `ikp-row` and the `slug-*` / `cid-*` classes are used only by
 * this script and have no CSS rules, so do not remove them as unused.
 *
 * Data from the build: each page embeds its search text as a JSON block
 * (`<script type="application/json" data-ikp="search-index">`), read by
 * `readSearchIndex` below. No page data lives in this file.
 *
 * Layout of this file:
 *   1. Helpers shared by the pages
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
  // an item key (a telescope slug or a contribution id slug) to lower-case
  // text to search in.
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

  // True if the space-separated `tokenStr` contains every token in `filters`
  // (whole tokens only, not parts of a token).
  function hasAllTokens(tokenStr, filters) {
    var tokens = ' ' + tokenStr + ' ';
    return filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; });
  }

  // Scroll a card into view and outline it for a moment.
  function highlightCard(card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    card.classList.add('ikp-highlight');
    setTimeout(function () { card.classList.remove('ikp-highlight'); }, 1500);
  }

  // Make the headers of `table` (those with a `data-sort` attribute) sort the
  // rows when clicked: first click ascending, second click on the same header
  // descending. The rows are compared by their `data-<key>` attribute.
  function wireTableSorting(table) {
    var sortState = {};
    table.querySelectorAll('th[data-sort]').forEach(function (th) {
      th.addEventListener('click', function () {
        var key = th.getAttribute('data-sort');
        var tbody = table.querySelector('tbody');
        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
        var asc = !sortState[key];
        sortState = {};
        sortState[key] = asc;
        rows.sort(function (a, b) {
          var av = a.getAttribute('data-' + key) || '';
          var bv = b.getAttribute('data-' + key) || '';
          return asc ? av.localeCompare(bv) : bv.localeCompare(av);
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
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
    var SEARCH_INDEX = readSearchIndex();

    function matchesSearch(slug) {
      var query = document.getElementById('ikt-search').value.trim().toLowerCase();
      if (!query) { return true; }
      var text = SEARCH_INDEX[slug] || '';
      return text.indexOf(query) !== -1;
    }

    function slugOfCard(card) {
      var m = card.className.match(/\bslug-(\S+)/);
      return m ? m[1] : '';
    }

    function applyFilters() {
      var instr = document.getElementById('ikt-filter-instr').value;
      var wl = document.getElementById('ikt-filter-wl').value;
      var resEl = document.getElementById('ikt-filter-res');  // absent when there are no resolution bins
      var res = resEl ? resEl.value : '';
      var multiplex = document.getElementById('ikt-filter-multiplex').value;
      var status = document.getElementById('ikt-filter-status').value;
      var hemisphere = document.getElementById('ikt-filter-hemisphere').value;
      var aperture = document.getElementById('ikt-filter-aperture').value;
      var filters = [instr, wl, res, multiplex, status, hemisphere, aperture].filter(Boolean);

      function matches(tokenStr, slug) {
        return hasAllTokens(tokenStr, filters) && matchesSearch(slug);
      }

      document.querySelectorAll('.ikp-row').forEach(function (row) {
        setVisible(row, matches(row.getAttribute('data-tokens'), row.querySelector('.ikp-title-link').getAttribute('data-slug')));
      });
      document.querySelectorAll('.ikp-card').forEach(function (card) {
        setVisible(card, matches(card.className, slugOfCard(card)));
      });
      document.querySelectorAll('.ikp-map-marker').forEach(function (marker) {
        setVisible(marker, matches(marker.getAttribute('data-tokens'), marker.getAttribute('data-slug')));
      });
    }

    ['ikt-filter-instr', 'ikt-filter-wl', 'ikt-filter-res', 'ikt-filter-multiplex', 'ikt-filter-status', 'ikt-filter-hemisphere', 'ikt-filter-aperture'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', applyFilters);
    });
    var searchInput = document.getElementById('ikt-search');
    if (searchInput) { searchInput.addEventListener('input', applyFilters); }

    function scrollToCard(slug) {
      var card = document.querySelector('.ikp-card.slug-' + CSS.escape(slug));
      if (!card) { return; }
      highlightCard(card);
    }

    document.querySelectorAll('.ikp-title-link').forEach(function (link) {
      link.addEventListener('click', function () { scrollToCard(link.getAttribute('data-slug')); });
    });
    document.querySelectorAll('.ikp-map-marker').forEach(function (marker) {
      marker.addEventListener('click', function () { scrollToCard(marker.getAttribute('data-slug')); });
    });

    wireTableSorting(table);
  }

  // -------------------------------------------------------------------------
  // 3. Datasets page
  // -------------------------------------------------------------------------
  function initDatasets(table) {
    var SEARCH_INDEX = readSearchIndex();
    // Rows and cards carry a `cid-<id>` token; it keys the search index.
    var CID_RE = /cid-([a-z0-9-]+)/;
    var showAvailableOnly = false;

    function matchesSearch(tokens) {
      var query = document.getElementById('ikc-search').value.trim().toLowerCase();
      if (!query) { return true; }
      var m = CID_RE.exec(tokens);
      var text = m ? (SEARCH_INDEX[m[1]] || '') : '';
      return text.indexOf(query) !== -1;
    }

    function applyFilters() {
      var dt = document.getElementById('ikc-filter-dt').value;
      var wl = document.getElementById('ikc-filter-wl').value;
      var uat = document.getElementById('ikc-filter-uat').value;
      var filters = [dt, wl, uat].filter(Boolean);
      if (showAvailableOnly) { filters.push('status-available'); }
      document.querySelectorAll('.ikp-row').forEach(function (row) {
        var tokenStr = row.getAttribute('data-tokens');
        setVisible(row, hasAllTokens(tokenStr, filters) && matchesSearch(tokenStr));
      });
      document.querySelectorAll('.ikp-card').forEach(function (card) {
        var tokenStr = card.className;
        setVisible(card, hasAllTokens(tokenStr, filters) && matchesSearch(tokenStr));
      });
    }
    ['ikc-filter-dt', 'ikc-filter-wl', 'ikc-filter-uat'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', applyFilters);
    });
    var searchInput = document.getElementById('ikc-search');
    if (searchInput) { searchInput.addEventListener('input', applyFilters); }

    var toggleBtn = document.getElementById('ikc-toggle-status');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        showAvailableOnly = !showAvailableOnly;
        toggleBtn.setAttribute('aria-pressed', showAvailableOnly ? 'true' : 'false');
        toggleBtn.textContent = showAvailableOnly ? 'Include future datasets' : 'Show available only';
        applyFilters();
      });
    }

    document.querySelectorAll('.ikp-title-link').forEach(function (link) {
      link.addEventListener('click', function () {
        var card = document.querySelector('.ikp-card.cid-' + link.getAttribute('data-cid'));
        if (!card) { return; }
        highlightCard(card);
      });
    });

    wireExpandButtons('.ikp-more-btn');
    wireTableSorting(table);
  }

  // -------------------------------------------------------------------------
  // 4. Software page
  // -------------------------------------------------------------------------
  function initSoftware(table) {
    var SEARCH_INDEX = readSearchIndex();
    var CID_RE = /cid-([a-z0-9-]+)/;

    function matchesSearch(tokens) {
      var query = document.getElementById('ikc-sw-search').value.trim().toLowerCase();
      if (!query) { return true; }
      var m = CID_RE.exec(tokens);
      var text = m ? (SEARCH_INDEX[m[1]] || '') : '';
      return text.indexOf(query) !== -1;
    }

    function applyFilters() {
      var cat = document.getElementById('ikc-sw-filter-cat').value;
      var uat = document.getElementById('ikc-sw-filter-uat').value;
      var recipient = document.getElementById('ikc-sw-filter-recipient').value;
      var status = document.getElementById('ikc-sw-filter-status').value;
      var filters = [cat, uat, recipient, status].filter(Boolean);
      document.querySelectorAll('#ikc-sw-table .ikp-row').forEach(function (row) {
        var tokenStr = row.getAttribute('data-tokens');
        setVisible(row, hasAllTokens(tokenStr, filters) && matchesSearch(tokenStr));
      });
      document.querySelectorAll('.ikp-sw-card').forEach(function (card) {
        var tokenStr = card.className;
        setVisible(card, hasAllTokens(tokenStr, filters) && matchesSearch(tokenStr));
      });
    }
    ['ikc-sw-filter-cat', 'ikc-sw-filter-uat', 'ikc-sw-filter-recipient', 'ikc-sw-filter-status'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', applyFilters);
    });
    var searchInput = document.getElementById('ikc-sw-search');
    if (searchInput) { searchInput.addEventListener('input', applyFilters); }

    document.querySelectorAll('.ikp-title-link').forEach(function (link) {
      link.addEventListener('click', function () {
        var card = document.querySelector('.ikp-sw-card.cid-' + link.getAttribute('data-cid'));
        if (!card) { return; }
        highlightCard(card);
      });
    });

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
