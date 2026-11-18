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

      <div class="ikp-filterbar">
        <label>Data type
          <select id="ikc-filter-dt">
            <option value="">All</option>
            {% for label, slug in all_data_types %}<option value="dt-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Wavelength
          <select id="ikc-filter-wl">
            <option value="">All</option>
            {% for label, slug in all_wavelengths %}<option value="wl-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Science case (UAT)
          <select id="ikc-filter-uat">
            <option value="">All</option>
            {% for label, slug in all_uat %}<option value="uat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
      </div>

      <div class="ikp-actionbar">
        <input type="text" id="ikc-search" placeholder="Search title, description, keywords...">
        <button type="button" id="ikc-toggle-status" class="ikp-toggle-btn" aria-pressed="false">Show available only</button>
      </div>

      <table class="ikp-datasets-table" id="ikc-datasets-table">
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
          <tr class="ikp-row" data-tokens="{{ ds.filter_tokens }}"
              data-title="{{ ds.title }}"
              data-datatype="{{ (ds.form_data.data_type or []) | join(', ') }}"
              data-wavelength="{{ (ds.curated.wavelength_regime or []) | join(', ') }}"
              data-recipient="{{ ds.curated.primary_recipient or '' }}"
              data-status="{{ ds.status }}"
              data-updated="{{ ds.last_updated or '' }}">
            <td><button type="button" class="ikp-title-link" data-cid="{{ ds.cid_slug }}">{{ ds.title }} ({{ ds.contribution_id }})</button></td>
            <td>{{ (ds.form_data.data_type or []) | join(', ') or 'TBD' }}</td>
            <td>{{ (ds.curated.wavelength_regime or []) | join(', ') or 'TBD' }}</td>
            <td>{{ ds.curated.primary_recipient or 'TBD' }}</td>
            <td>{% if ds.status == 'available' %}<span class="ikp-badge ikp-badge-success">Available</span>{% else %}<span class="ikp-badge ikp-badge-muted">Not yet delivered</span>{% endif %}</td>
            <td>{{ ds.last_updated or 'unknown' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script>
      document.addEventListener('DOMContentLoaded', function () {
        // Deferred to DOMContentLoaded: this script tag renders above the
        // `.. grid::` block below, which is where the cards (and their
        // Show more/Show less buttons) actually live in the page source.
        // An inline <script> runs the instant the parser reaches it, so
        // querying for card elements here immediately (rather than after
        // the whole page has parsed) would always find zero of them --
        // same bug as the Contributed Software page's expand button had.
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
          document.querySelectorAll('.ikp-row').forEach(function (row) {
            var tokenStr = row.getAttribute('data-tokens');
            var tokens = ' ' + tokenStr + ' ';
            var visible = filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(tokenStr);
            setVisible(row, visible);
          });
          document.querySelectorAll('.ikp-card').forEach(function (card) {
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

        document.querySelectorAll('.ikp-title-link').forEach(function (link) {
          link.addEventListener('click', function () {
            var cid = link.getAttribute('data-cid');
            var card = document.querySelector('.ikp-card.cid-' + cid);
            if (!card) { return; }
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            card.classList.add('ikp-highlight');
            setTimeout(function () { card.classList.remove('ikp-highlight'); }, 1500);
          });
        });

        document.querySelectorAll('.ikp-more-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var moreFields = btn.previousElementSibling;
            var expanded = moreFields.classList.toggle('ikp-expanded');
            btn.textContent = expanded
              ? btn.getAttribute('data-collapse-label')
              : btn.getAttribute('data-expand-label');
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
      });
      </script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for ds in datasets %}
      {% if ds.status == 'available' %}
      .. _ds-cid-{{ ds.cid_slug }}:

      .. grid-item-card:: {{ ds.title }}
          :class-item: ikp-card {{ ds.filter_tokens }}

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

          **Maintenance plan:** {{ ds.form_data.maintenance_plan or 'TBD' }}

          .. container:: ikp-more-fields

             **Data schema:** {{ ds.form_data.data_schema_link or 'TBD' }}

             **Access mechanisms:** {{ (ds.form_data.access_mechanisms or []) | join(', ') or 'TBD' }}

             **Authentication:** {{ ds.form_data.authentication or 'TBD' }}

             **Generation methods:** {{ ds.form_data.generation_methods or 'TBD' }}

             **Validation & limitations:** {{ ds.form_data.validation_limitations or 'TBD' }}

          .. raw:: html

             <button type="button" class="ikp-more-btn" data-expand-label="Show more" data-collapse-label="Show less">Show more</button>

          {% for rel in ds.related %}
          {% if rel.page_url %}

          .. raw:: html

             <a class="ikp-also-see" href="{{ rel.page_url }}#sw-cid-{{ rel.slug }}">Also see: software ({{ rel.contribution_id }}) &rarr;</a>

          {% endif %}
          {% endfor %}

          *Updated: {{ ds.last_updated or 'unknown' }}*
          +++
          :bdg-success:`Available`
      {% else %}
      .. _ds-cid-{{ ds.cid_slug }}:

      .. grid-item-card:: {{ ds.title }}
          :class-item: ikp-card {{ ds.filter_tokens }}

          {{ ds.contribution_id }} - {{ ds.country }}
          ^^^
          {% for dt in (ds.form_data.data_type or []) %}:bdg-light:`{{ dt }}` {% endfor %}{% for wl in (ds.curated.wavelength_regime or []) %}:bdg-light:`{{ wl }}` {% endfor %}{% for uc in (ds.form_data.uat_category or []) %}:bdg-light:`{{ uc }}` {% endfor %}

          {{ ds.curated.summary or 'TBD' }}

          **Primary recipient:** {{ ds.curated.primary_recipient or 'TBD' }}

          {% for rel in ds.related %}
          {% if rel.page_url %}

          .. raw:: html

             <a class="ikp-also-see" href="{{ rel.page_url }}#sw-cid-{{ rel.slug }}">Also see: software ({{ rel.contribution_id }}) &rarr;</a>

          {% endif %}
          {% endfor %}

          *Updated: {{ ds.last_updated or 'unknown' }}*
          +++
          :bdg-muted:`Not yet delivered`
      {% endif %}
      {% endfor %}
