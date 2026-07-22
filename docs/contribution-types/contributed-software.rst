######################
Contributed Software
######################

The Vera C. Rubin Observatory In-Kind Program includes contributed software: directable and non-directable software-development effort that international partners contribute to Rubin teams and LSST Science Collaborations.
This page lists all current software-development contributions. General pool contributions -- directable effort offered without a recipient defined ahead of time -- are listed on the :doc:`general-pool` page instead.

Use the filters or the table below to browse by category, science keyword, or recipient group.
Each entry starts with the basics from the original proposal; cards marked *Delivered* have a full team-submitted record on file, and cards marked *Pending* are still awaiting that submission.
Some software contributions also produce a dataset -- where that's the case, the card links to the matching entry on the :doc:`contributed-datasets` page.

Please email the in-kind helpdesk rubin-inkind at noirlab dot edu if you have any questions about contributed software.

.. jinja:: contributed_software

   .. raw:: html

      <style>
        .ikc-filterbar { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; }
        .ikc-filterbar label { font-size: 0.9em; }
        .ikc-sw-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        .ikc-sw-table th, .ikc-sw-table td { text-align: left; padding: 0.5em 0.75em; border-bottom: 1px solid #ddd; }
        .ikc-sw-table th { cursor: pointer; user-select: none; }
        .ikc-badge { display: inline-block; padding: 0.15em 0.6em; border-radius: 1em; font-size: 0.85em; }
        .ikc-badge-success { background: #d9f2e3; color: #1a5c33; }
        .ikc-badge-muted { background: #e6e6e6; color: #555; }
        .ikc-actionbar { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; margin-bottom: 1rem; }
        .ikc-actionbar input[type="text"] { flex: 1; min-width: 220px; padding: 0.4em 0.6em; border: 1px solid #999; border-radius: 0.3em; font-size: 0.9em; }
        .ikc-title-link { color: inherit; text-decoration: none; cursor: pointer; background: none; border: none; padding: 0; font: inherit; text-align: left; }
        .ikc-title-link:hover { text-decoration: underline; }
        .ikc-sw-card.ikc-highlight .sd-card { outline: 3px solid #1a5c33; outline-offset: 2px; transition: outline-color 1.2s ease; }
        .ikc-desc { -webkit-line-clamp: 3; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 0.4em; }
        .ikc-desc.ikc-expanded { -webkit-line-clamp: unset; display: block; overflow: visible; }
        .ikc-expand-btn { border: none; background: none; color: #1a5c33; font-size: 0.85em; padding: 0; cursor: pointer; margin-bottom: 0.6em; }
        .ikc-also-see { display: block; background: #e6e6e6; color: #333; font-size: 0.85em; padding: 0.3em 0.7em; border-radius: 1em; margin-top: 0.5em; text-decoration: none; }
        .ikc-also-see:hover { background: #d9d9d9; }
      </style>

      <div class="ikc-filterbar">
        <label>Category
          <select id="ikc-sw-filter-cat">
            <option value="">All</option>
            {% for v in all_categories %}<option value="cat-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>UAT keyword
          <select id="ikc-sw-filter-uat">
            <option value="">All</option>
            {% for v in all_uat %}<option value="uat-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Primary recipient
          <select id="ikc-sw-filter-recipient">
            <option value="">All</option>
            {% for v in all_recipients %}<option value="recipient-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Status
          <select id="ikc-sw-filter-status">
            <option value="">All</option>
            <option value="status-delivered">Delivered</option>
            <option value="status-pending">Pending</option>
          </select>
        </label>
      </div>

      <div class="ikc-actionbar">
        <input type="text" id="ikc-sw-search" placeholder="Search title, description, keywords...">
      </div>

      <table class="ikc-sw-table" id="ikc-sw-table">
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
          <tr class="ikc-row" data-tokens="{{ item.filter_tokens }}"
              data-title="{{ item.title }}"
              data-category="{{ item.form_data.category or '' }}"
              data-recipient="{{ item.form_data.primary_recipient_group or '' }}"
              data-status="{{ item.status }}"
              data-updated="{{ item.last_updated or '' }}">
            <td><button type="button" class="ikc-title-link" data-cid="{{ item.cid_slug }}">{{ item.title }} ({{ item.contribution_id }})</button></td>
            <td>{{ item.form_data.category or 'TBD' }}</td>
            <td>{{ item.form_data.primary_recipient_group or 'TBD' }}</td>
            <td>{% if item.status == 'delivered' %}<span class="ikc-badge ikc-badge-success">Delivered</span>{% else %}<span class="ikc-badge ikc-badge-muted">Pending</span>{% endif %}</td>
            <td>{{ item.last_updated or 'unknown' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script>
      (function () {
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
          document.querySelectorAll('#ikc-sw-table .ikc-row').forEach(function (row) {
            var tokenStr = row.getAttribute('data-tokens');
            var tokens = ' ' + tokenStr + ' ';
            var visible = filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(tokenStr);
            setVisible(row, visible);
          });
          document.querySelectorAll('.ikc-sw-card').forEach(function (card) {
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

        document.querySelectorAll('.ikc-title-link').forEach(function (link) {
          link.addEventListener('click', function () {
            var cid = link.getAttribute('data-cid');
            var card = document.querySelector('.ikc-sw-card.cid-' + cid);
            if (!card) { return; }
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            card.classList.add('ikc-highlight');
            setTimeout(function () { card.classList.remove('ikc-highlight'); }, 1500);
          });
        });

        document.querySelectorAll('.ikc-expand-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var desc = btn.previousElementSibling;
            var expanded = desc.classList.toggle('ikc-expanded');
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
      })();
      </script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for item in software %}
      .. _sw-cid-{{ item.cid_slug }}:

      .. grid-item-card:: {{ item.title }}
          :class-item: ikc-sw-card ikc-card {{ item.filter_tokens }}

          {{ item.contribution_id }}
          ^^^
          {% for kw in item.uat_keywords %}:bdg-light:`{{ kw }}` {% endfor %}

          **Primary recipient:** {{ item.form_data.primary_recipient_group or 'TBD' }}

          **Additional recipients:** {{ (item.form_data.additional_recipient_groups or []) | join(', ') or 'None' }}

          {% if item.form_data.software_name %}**Software:** {{ item.form_data.software_name }}{% endif %}

          .. raw:: html

             <div class="ikc-desc">{{ item.form_data.activity_description or 'TBD' }}</div>
             <button type="button" class="ikc-expand-btn" data-expand-label="Show more" data-collapse-label="Show less">Show more</button>

          {% for rel in item.related %}
          {% if rel.page_url %}
          `Also see: {{ rel.title }} ({{ rel.contribution_id }}) → <{{ rel.page_url }}#ds-cid-{{ rel.slug }}>`_
          {% endif %}
          {% endfor %}

          *Updated: {{ item.last_updated or 'unknown' }}*
          +++
          {% if item.status == 'delivered' %}:bdg-success:`Delivered`{% else %}:bdg-muted:`Pending`{% endif %}
      {% endfor %}
