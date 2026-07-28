########
Datasets
########

The Vera C. Rubin Observatory In-Kind Program includes contributed datasets: complementary data products that international partners make available to the Rubin community in exchange for data rights.
This page lists all current dataset contributions, helping the Rubin and NOIRLab community discover data relevant to their research.

Use the filters or the table below to browse by data type, wavelength regime, or science case.
Each entry links to a fuller record with access details, documentation, and citation information once a dataset is ready to share.
Most contributions are still pre-delivery; those are clearly marked and will be filled in as datasets become available.

Please email the in-kind helpdesk rubin-inkind at noirlab dot edu if you have any questions about contributed datasets.

.. jinja:: contributed_datasets

   .. raw:: html

      <style>
        .ikc-filterbar { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; }
        .ikc-filterbar label { font-size: 0.9em; }
        .ikc-datasets-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        .ikc-datasets-table th, .ikc-datasets-table td { text-align: left; padding: 0.5em 0.75em; border-bottom: 1px solid #ddd; }
        .ikc-datasets-table th { cursor: pointer; user-select: none; }
        .ikc-badge { display: inline-block; padding: 0.15em 0.6em; border-radius: 1em; font-size: 0.85em; }
        .ikc-badge-success { background: #d9f2e3; color: #1a5c33; }
        .ikc-badge-muted { background: #e6e6e6; color: #555; }
        .ikc-toggle-btn { padding: 0.4em 0.9em; border-radius: 1em; border: 1px solid #999; background: #fff; color: #1a1a1a; cursor: pointer; font-size: 0.9em; white-space: nowrap; }
        .ikc-toggle-btn[aria-pressed="true"] { background: #1a5c33; border-color: #1a5c33; color: #fff; }
        .ikc-actionbar { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; margin-bottom: 1rem; }
        .ikc-actionbar input[type="text"] { flex: 1; min-width: 220px; padding: 0.4em 0.6em; border: 1px solid #999; border-radius: 0.3em; font-size: 0.9em; }
        .ikc-title-link { color: inherit; text-decoration: none; cursor: pointer; background: none; border: none; padding: 0; font: inherit; text-align: left; }
        .ikc-title-link:hover { text-decoration: underline; }
        .ikc-card.ikc-highlight .sd-card { outline: 3px solid #1a5c33; outline-offset: 2px; transition: outline-color 1.2s ease; }
      </style>

      <div class="ikc-filterbar">
        <label>Data type
          <select id="ikc-filter-dt">
            <option value="">All</option>
            {% for v in all_data_types %}<option value="dt-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Wavelength
          <select id="ikc-filter-wl">
            <option value="">All</option>
            {% for v in all_wavelengths %}<option value="wl-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Science case (UAT)
          <select id="ikc-filter-uat">
            <option value="">All</option>
            {% for v in all_uat %}<option value="uat-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
      </div>

      <div class="ikc-actionbar">
        <input type="text" id="ikc-search" placeholder="Search title, description, keywords...">
        <button type="button" id="ikc-toggle-status" class="ikc-toggle-btn" aria-pressed="false">Show available only</button>
      </div>

      <table class="ikc-datasets-table" id="ikc-datasets-table">
        <thead>
          <tr>
            <th data-sort="title">Dataset</th>
            <th data-sort="datatype">Data type</th>
            <th data-sort="wavelength">Wavelength</th>
            <th data-sort="recipient">Primary recipient</th>
            <th data-sort="status">Status</th>
            <th data-sort="updated">Updated</th>
          </tr>
        </thead>
        <tbody>
          {% for ds in datasets %}
          <tr class="ikc-row" data-tokens="{{ ds.filter_tokens }}"
              data-title="{{ ds.title }}"
              data-datatype="{{ (ds.form_data.data_type or []) | join(', ') }}"
              data-wavelength="{{ (ds.curated.wavelength_regime or []) | join(', ') }}"
              data-recipient="{{ ds.curated.primary_recipient or '' }}"
              data-status="{{ ds.status }}"
              data-updated="{{ ds.last_updated or '' }}">
            <td><button type="button" class="ikc-title-link" data-cid="{{ ds.cid_slug }}">{{ ds.title }} ({{ ds.contribution_id }})</button></td>
            <td>{{ (ds.form_data.data_type or []) | join(', ') or 'TBD' }}</td>
            <td>{{ (ds.curated.wavelength_regime or []) | join(', ') or 'TBD' }}</td>
            <td>{{ ds.curated.primary_recipient or 'TBD' }}</td>
            <td>{% if ds.status == 'available' %}<span class="ikc-badge ikc-badge-success">Available</span>{% else %}<span class="ikc-badge ikc-badge-muted">Not yet delivered</span>{% endif %}</td>
            <td>{{ ds.last_updated or 'unknown' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script>
      (function () {
        var SEARCH_INDEX = {{ search_index_json }};
        var CID_RE = /cid-([a-z0-9-]+)/;
        var showAvailableOnly = false;

        function matchesSearch(tokens) {
          var query = document.getElementById('ikc-search').value.trim().toLowerCase();
          if (!query) { return true; }
          var m = CID_RE.exec(tokens);
          var text = m ? (SEARCH_INDEX[m[1]] || '') : '';
          return text.indexOf(query) !== -1;
        }

        function setVisible(el, visible) {
          // sphinx-design's grid-item wrapper carries a `display: flex
          // !important` class (.sd-d-flex-row), which beats a plain inline
          // `style="display:none"`. Setting the inline override with
          // !important priority is the only thing that reliably wins.
          if (visible) {
            el.style.removeProperty('display');
          } else {
            el.style.setProperty('display', 'none', 'important');
          }
        }

        function applyFilters() {
          var dt = document.getElementById('ikc-filter-dt').value;
          var wl = document.getElementById('ikc-filter-wl').value;
          var uat = document.getElementById('ikc-filter-uat').value;
          var filters = [dt, wl, uat].filter(Boolean);
          if (showAvailableOnly) { filters.push('status-available'); }
          document.querySelectorAll('.ikc-row').forEach(function (row) {
            var tokenStr = row.getAttribute('data-tokens');
            var tokens = ' ' + tokenStr + ' ';
            var visible = filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(tokenStr);
            setVisible(row, visible);
          });
          document.querySelectorAll('.ikc-card').forEach(function (card) {
            var tokenStr = card.className;
            var tokens = ' ' + tokenStr + ' ';
            var visible = filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(tokenStr);
            setVisible(card, visible);
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

        document.querySelectorAll('.ikc-title-link').forEach(function (link) {
          link.addEventListener('click', function () {
            var cid = link.getAttribute('data-cid');
            var card = document.querySelector('.ikc-card.cid-' + cid);
            if (!card) { return; }
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            card.classList.add('ikc-highlight');
            setTimeout(function () { card.classList.remove('ikc-highlight'); }, 1500);
          });
        });

        var sortState = {};
        document.querySelectorAll('#ikc-datasets-table th[data-sort]').forEach(function (th) {
          th.addEventListener('click', function () {
            var key = th.getAttribute('data-sort');
            var tbody = document.querySelector('#ikc-datasets-table tbody');
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
      })();
      </script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for ds in datasets %}
      {% if ds.status == 'available' %}
      .. _ds-cid-{{ ds.cid_slug }}:

      .. grid-item-card:: {{ ds.title }}
          :class-item: ikc-card {{ ds.filter_tokens }}

          {{ ds.contribution_id }} - {{ ds.country }}
          ^^^
          {% for dt in (ds.form_data.data_type or []) %}:bdg-light:`{{ dt }}` {% endfor %}{% for wl in (ds.curated.wavelength_regime or []) %}:bdg-light:`{{ wl }}` {% endfor %}{% for uc in (ds.form_data.uat_category or []) %}:bdg-light:`{{ uc }}` {% endfor %}

          **Primary recipient:** {{ ds.curated.primary_recipient or 'TBD' }}

          **Target audience:** {{ ds.curated.target_audience or ds.form_data.target_audience or 'TBD' }}

          {{ ds.curated.summary or 'TBD' }}

          **Data volume:** {{ ds.form_data.data_volume or 'TBD' }}

          **Hosting location:** {{ ds.form_data.hosting_location or 'TBD' }}

          **Access:** {{ ds.form_data.access_url or 'TBD' }}

          **Documentation:** {{ ds.form_data.tutorials_docs or 'TBD' }}

          **Support channel:** {{ ds.form_data.support_channel or 'TBD' }}

          **Citation:** {{ ds.form_data.citation or 'TBD' }}

          *Updated: {{ ds.last_updated or 'unknown' }}*
          +++
          :bdg-success:`Available`
      {% else %}
      .. _ds-cid-{{ ds.cid_slug }}:

      .. grid-item-card:: {{ ds.title }}
          :class-item: ikc-card {{ ds.filter_tokens }}

          {{ ds.contribution_id }} - {{ ds.country }}
          ^^^
          {% for dt in (ds.form_data.data_type or []) %}:bdg-light:`{{ dt }}` {% endfor %}{% for wl in (ds.curated.wavelength_regime or []) %}:bdg-light:`{{ wl }}` {% endfor %}{% for uc in (ds.form_data.uat_category or []) %}:bdg-light:`{{ uc }}` {% endfor %}

          {{ ds.curated.summary or 'TBD' }}

          **Primary recipient:** {{ ds.curated.primary_recipient or 'TBD' }}

          *Updated: {{ ds.last_updated or 'unknown' }}*
          +++
          :bdg-muted:`Not yet delivered`
      {% endif %}
      {% endfor %}
