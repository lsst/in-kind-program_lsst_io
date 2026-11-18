########
Software
########

The Vera C. Rubin Observatory In-Kind Program includes contributed software: directable and non-directable software-development effort that international partners contribute to Rubin teams and LSST Science Collaborations.
This page lists all current software-development contributions. General pool contributions -- directable effort offered without a recipient defined ahead of time -- are listed on the :doc:`general-pool` page instead.

Use the filters or the table below to browse by category, science keyword, or recipient group.
Each entry starts with the basics from the original proposal; cards marked *Delivered* have a full team-submitted record on file, and cards marked *In Progress* are still awaiting that submission.
Some software contributions also produce a dataset -- where that's the case, the card links to the matching entry on the :doc:`contributed-datasets` page.

Please email the in-kind helpdesk rubin-inkind at noirlab dot edu if you have any questions about contributed software.

.. jinja:: contributed_software

   .. raw:: html

      <div class="ikp-filterbar">
        <label>Category
          <select id="ikc-sw-filter-cat">
            <option value="">All</option>
            {% for label, slug in all_categories %}<option value="cat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>UAT keyword
          <select id="ikc-sw-filter-uat">
            <option value="">All</option>
            {% for label, slug in all_uat %}<option value="uat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Primary recipient
          <select id="ikc-sw-filter-recipient">
            <option value="">All</option>
            {% for label, slug in all_recipients %}<option value="recipient-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Status
          <select id="ikc-sw-filter-status">
            <option value="">All</option>
            <option value="status-delivered">Delivered</option>
            <option value="status-pending">In Progress</option>
          </select>
        </label>
      </div>

      <div class="ikp-actionbar">
        <input type="text" id="ikc-sw-search" placeholder="Search title, description, keywords...">
      </div>

      <table class="ikp-sw-table" id="ikc-sw-table">
        <thead>
          <tr>
            <th data-sort="title">Software</th>
            <th data-sort="category">Category</th>
            <th data-sort="recipient">Primary recipient</th>
            <th data-sort="status">Status</th>
            <th data-sort="updated">Updated</th>
          </tr>
        </thead>
        <tbody>
          {% for item in software %}
          <tr class="ikp-row" data-tokens="{{ item.filter_tokens }}"
              data-title="{{ item.title }}"
              data-category="{{ item.form_data.category or '' }}"
              data-recipient="{{ item.form_data.primary_recipient_group or '' }}"
              data-status="{{ item.status }}"
              data-updated="{{ item.last_updated or '' }}">
            <td><button type="button" class="ikp-title-link" data-cid="{{ item.cid_slug }}">{{ item.title }} ({{ item.contribution_id }})</button></td>
            <td>{{ item.form_data.category or 'TBD' }}</td>
            <td>{{ item.form_data.primary_recipient_group or 'TBD' }}</td>
            <td>{% if item.status == 'delivered' %}<span class="ikp-badge ikp-badge-success">Delivered</span>{% else %}<span class="ikp-badge ikp-badge-muted">In Progress</span>{% endif %}</td>
            <td>{{ item.last_updated or 'unknown' }}</td>
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
        // that's why the expand button did nothing.
        var SEARCH_INDEX = {{ search_index_json }};
        var CID_RE = /cid-([a-z0-9-]+)/;

        function matchesSearch(tokens) {
          var query = document.getElementById('ikc-sw-search').value.trim().toLowerCase();
          if (!query) { return true; }
          var m = CID_RE.exec(tokens);
          var text = m ? (SEARCH_INDEX[m[1]] || '') : '';
          return text.indexOf(query) !== -1;
        }

        function setVisible(el, visible) {
          if (visible) {
            el.style.removeProperty('display');
          } else {
            el.style.setProperty('display', 'none', 'important');
          }
        }

        function applyFilters() {
          var cat = document.getElementById('ikc-sw-filter-cat').value;
          var uat = document.getElementById('ikc-sw-filter-uat').value;
          var recipient = document.getElementById('ikc-sw-filter-recipient').value;
          var status = document.getElementById('ikc-sw-filter-status').value;
          var filters = [cat, uat, recipient, status].filter(Boolean);
          document.querySelectorAll('#ikc-sw-table .ikp-row').forEach(function (row) {
            var tokenStr = row.getAttribute('data-tokens');
            var tokens = ' ' + tokenStr + ' ';
            var visible = filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(tokenStr);
            setVisible(row, visible);
          });
          document.querySelectorAll('.ikp-sw-card').forEach(function (card) {
            var tokenStr = card.className;
            var tokens = ' ' + tokenStr + ' ';
            var visible = filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(tokenStr);
            setVisible(card, visible);
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
            var cid = link.getAttribute('data-cid');
            var card = document.querySelector('.ikp-sw-card.cid-' + cid);
            if (!card) { return; }
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            card.classList.add('ikp-highlight');
            setTimeout(function () { card.classList.remove('ikp-highlight'); }, 1500);
          });
        });

        document.querySelectorAll('.ikp-expand-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var desc = btn.previousElementSibling;
            var expanded = desc.classList.toggle('ikp-expanded');
            btn.textContent = expanded
              ? btn.getAttribute('data-collapse-label')
              : btn.getAttribute('data-expand-label');
          });
        });

        var sortState = {};
        document.querySelectorAll('#ikc-sw-table th[data-sort]').forEach(function (th) {
          th.addEventListener('click', function () {
            var key = th.getAttribute('data-sort');
            var tbody = document.querySelector('#ikc-sw-table tbody');
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

      {% for item in software %}
      .. _sw-cid-{{ item.cid_slug }}:

      .. grid-item-card:: {{ item.title }}
          :class-item: ikp-sw-card ikp-card {{ item.filter_tokens }}

          {{ item.contribution_id }}
          ^^^
          {% for kw in item.uat_keywords %}:bdg-light:`{{ kw }}` {% endfor %}

          **Primary recipient:** {{ item.form_data.primary_recipient_group or 'TBD' }}

          **Additional recipients:** {{ (item.form_data.additional_recipient_groups or []) | join(', ') or 'None' }}

          {% if item.form_data.software_name %}**Software:** {{ item.form_data.software_name }}{% endif %}

          {% if item.approx_start %}**Start (approx.):** {{ item.approx_start }}{% endif %}

          {% if item.software_links %}**Links:** {% for link in item.software_links %}`{{ link.label }} <{{ link.url }}>`__{{ ", " if not loop.last else "" }}{% endfor %}{% endif %}

          {% if item.documentation_links %}**Documentation:** {% for link in item.documentation_links %}`{{ link.label }} <{{ link.url }}>`__{{ ", " if not loop.last else "" }}{% endfor %}{% endif %}

          .. raw:: html

             <div class="ikp-desc">{{ item.form_data.activity_description or 'TBD' }}</div>
             <button type="button" class="ikp-expand-btn" data-expand-label="Show more" data-collapse-label="Show less">Show more</button>

          {% for rel in item.related %}
          {% if rel.page_url %}

          .. raw:: html

             <a class="ikp-also-see" href="{{ rel.page_url }}#{{ rel.anchor }}">Also see: dataset ({{ rel.contribution_id }}) &rarr;</a>

          {% endif %}
          {% endfor %}

          *Updated: {{ item.last_updated or 'unknown' }}*
          +++
          {% if item.status == 'delivered' %}:bdg-success:`Delivered`{% else %}:bdg-muted:`In Progress`{% endif %}
      {% endfor %}
