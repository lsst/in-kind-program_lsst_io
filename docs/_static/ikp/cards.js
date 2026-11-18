/*
 * cards.js: shared behaviour for the card pages of the In-Kind Program site
 * (Telescope Access, Datasets and Software): filters, search, sorting,
 * jump-to-card highlighting and the "Show more" buttons.
 *
 * Sphinx adds this file to every page of the site (see conf.py), so it must do
 * nothing on a page that has no cards. Each page's setup below runs only when
 * that page's own root element is present.
 *
 * The file is loaded with `defer`, so the whole page has been parsed before it
 * runs. The Computing Resources (IDAC) page keeps its own inline script and
 * does not use this file.
 */
(function () {
  'use strict';

  function init() {
    // Per-page setup functions are added in later commits.
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
