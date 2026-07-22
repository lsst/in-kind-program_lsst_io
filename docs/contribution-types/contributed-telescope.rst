################
Telescope Access
################

This page lists the facilities expected to be made available via the Vera C. Rubin Observatory In-kind Program.
The information on this page is subject to change. Final information on resources, time availability, and other pertinent information will be provided as part of the `NOIRLab Call for Proposals <https://noirlab.edu/science/observing-noirlab/proposals>`_ each semester.
Unless otherwise noted, this time will be made available via the NOIRLab Time Allocation Process.

Use the filters, search, or map below to find facilities relevant to your science case.

Please email the in-kind helpdesk rubin-inkind at noirlab dot edu if you have any questions about contributed telescope access.

.. jinja:: contributed_opportunities

   {% if opportunities %}
   .. raw:: html

      <style>
        .ikt-opp-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .ikt-opp-card { border: 2px solid #1a5c33; border-radius: 0.75rem; padding: 1rem 1.25rem; background: #f3faf6; }
        .ikt-opp-title { font-weight: 600; margin: 0 0 0.4em; }
        .ikt-opp-milestones { list-style: none; margin: 0.6em 0; padding: 0; font-size: 0.9em; }
        .ikt-opp-milestones li { padding: 0.15em 0; }
        .ikt-opp-milestones .approx::after { content: " (approx.)"; color: #666; }
        .ikt-opp-links a { margin-right: 1em; font-size: 0.9em; }
      </style>

      <div class="ikt-opp-row">
      {% for opp in opportunities %}
        <div class="ikt-opp-card" id="opp-{{ opp.slug }}">
          <p class="ikt-opp-title">{{ opp.title }}</p>
          <p>{{ opp.summary }}</p>
          {% if opp.milestones %}
          <ul class="ikt-opp-milestones">
            {% for m in opp.milestones %}
            <li{% if m.get('approximate') %} class="approx"{% endif %}><strong>{{ m.date }}</strong> &mdash; {{ m.label }}</li>
            {% endfor %}
          </ul>
          {% endif %}
          <div class="ikt-opp-links">
          {% for link in (opp.links or []) %}
            <a href="{{ link.url }}">{{ link.label }}</a>
          {% endfor %}
          </div>
          {% if opp.related_contribution_ids %}
          <p style="font-size: 0.85em; color: #666; margin-top: 0.6em;">
            Related facility:
            {% for cid in opp.related_contribution_ids %}
              {% for slug in (cid_to_slugs.get(cid) or []) %}<a href="#{{ slug }}">{{ cid }}</a> {% endfor %}
            {% endfor %}
          </p>
          {% endif %}
        </div>
      {% endfor %}
      </div>
   {% endif %}

.. jinja:: contributed_telescopes

   .. raw:: html

      <style>
        .ikt-filterbar { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; }
        .ikt-filterbar label { font-size: 0.9em; }
        .ikt-actionbar { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }
        .ikt-actionbar input[type="text"] { flex: 1; min-width: 220px; padding: 0.4em 0.6em; border: 1px solid #999; border-radius: 0.3em; font-size: 0.9em; }
        .ikt-map-wrap { margin-bottom: 1.5rem; border-radius: 0.5rem; overflow: hidden; background: #eef2f0; }
        .ikt-map-marker { cursor: pointer; }
        .ikt-map-marker:hover { stroke: #1a1a1a; stroke-width: 1.5; }
        .ikt-telescopes-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        .ikt-telescopes-table th, .ikt-telescopes-table td { text-align: left; padding: 0.5em 0.75em; border-bottom: 1px solid #ddd; }
        .ikt-telescopes-table th { cursor: pointer; user-select: none; }
        .ikt-badge { display: inline-block; padding: 0.15em 0.6em; border-radius: 1em; font-size: 0.85em; margin: 0 0.2em 0.2em 0; }
        .ikt-badge-success { background: #d9f2e3; color: #1a5c33; }
        .ikt-badge-muted { background: #e6e6e6; color: #555; }
        .ikt-badge-warning { background: #fdeecb; color: #8a5a00; }
        .ikt-title-link { color: inherit; text-decoration: none; cursor: pointer; background: none; border: none; padding: 0; font: inherit; text-align: left; }
        .ikt-title-link:hover { text-decoration: underline; }
        .ikt-card.ikt-highlight .sd-card { outline: 3px solid #1a5c33; outline-offset: 2px; transition: outline-color 1.2s ease; }
        .ikt-siblings { font-size: 0.85em; color: #555; margin-top: 0.6em; }
      </style>

      <div class="ikt-filterbar">
        <label>Instrumentation
          <select id="ikt-filter-instr">
            <option value="">All</option>
            {% for v in all_instrumentation %}<option value="instr-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Wavelength
          <select id="ikt-filter-wl">
            <option value="">All</option>
            {% for v in all_wavelengths %}<option value="wl-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Resolution
          <select id="ikt-filter-res">
            <option value="">All</option>
            {% for key, label in all_resolution_bins %}<option value="res-{{ key }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Multiplex
          <select id="ikt-filter-multiplex">
            <option value="">All</option>
            <option value="multiplex-yes">Yes</option>
          </select>
        </label>
        <label>Status
          <select id="ikt-filter-status">
            <option value="">All</option>
            <option value="status-available">Available</option>
            <option value="status-future-semester">Future semester</option>
          </select>
        </label>
        <label>Hemisphere
          <select id="ikt-filter-hemisphere">
            <option value="">All</option>
            <option value="hemisphere-northern">Northern</option>
            <option value="hemisphere-southern">Southern</option>
          </select>
        </label>
        <label>Aperture
          <select id="ikt-filter-aperture">
            <option value="">All</option>
            {% for key, label in all_aperture_bands %}<option value="aperture-{{ key }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
      </div>

      <div class="ikt-actionbar">
        <input type="text" id="ikt-search" placeholder="Search facilities, sites, instruments...">
      </div>

      <div class="ikt-map-wrap">
        <svg viewBox="0 0 1000 500" width="100%" height="320" role="img" aria-label="World map showing facility locations">
          <rect x="0" y="0" width="1000" height="500" fill="#eef2f0"></rect>
          {% if world_outline_path %}
          <path d="{{ world_outline_path }}" fill="#d7ded9" stroke="#c3ccc5" stroke-width="0.5"></path>
          {% endif %}
          {% for t in telescopes %}
          {% if t.marker_x is not none %}
          <circle class="ikt-map-marker" data-slug="{{ t.slug }}" data-tokens="{{ t.filter_tokens }}"
                  cx="{{ t.marker_x }}" cy="{{ t.marker_y }}" r="6"
                  fill="{{ '#1a5c33' if t.status == 'available' else '#8a5a00' }}"></circle>
          {% endif %}
          {% endfor %}
        </svg>
      </div>

      <table class="ikt-telescopes-table" id="ikt-telescopes-table">
        <thead>
          <tr>
            <th data-sort="facility">Facility</th>
            <th data-sort="location">Location</th>
            <th data-sort="instrumentation">Instrumentation</th>
            <th data-sort="status">Status</th>
            <th data-sort="aperture">Aperture</th>
          </tr>
        </thead>
        <tbody>
          {% for t in telescopes %}
          <tr class="ikt-row" data-tokens="{{ t.filter_tokens }}"
              data-facility="{{ t.facility }}"
              data-location="{{ [t.site, t.country] | select | join(', ') }}"
              data-instrumentation="{{ (t.instrumentation or []) | join(', ') }}"
              data-status="{{ t.status }}"
              data-aperture="{{ t.aperture or '' }}">
            <td><button type="button" class="ikt-title-link" data-slug="{{ t.slug }}">{{ t.facility }}</button></td>
            <td>{{ [t.site, t.country] | select | join(', ') }}</td>
            <td>{{ (t.instrumentation or []) | join(', ') or 'TBA' }}</td>
            <td>{% if t.status == 'available' %}<span class="ikt-badge ikt-badge-success">Available</span>{% else %}<span class="ikt-badge ikt-badge-warning">Future semester</span>{% endif %}</td>
            <td>{{ t.aperture or 'TBA' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script>
      (function () {
        var SEARCH_INDEX = {{ search_index_json }};

        function matchesSearch(slug) {
          var query = document.getElementById('ikt-search').value.trim().toLowerCase();
          if (!query) { return true; }
          var text = SEARCH_INDEX[slug] || '';
          return text.indexOf(query) !== -1;
        }

        function setVisible(el, visible) {
          if (visible) {
            el.style.removeProperty('display');
          } else {
            el.style.setProperty('display', 'none', 'important');
          }
        }

        function slugOfCard(card) {
          var m = card.className.match(/\bslug-(\S+)/);
          return m ? m[1] : '';
        }

        function applyFilters() {
          var instr = document.getElementById('ikt-filter-instr').value;
          var wl = document.getElementById('ikt-filter-wl').value;
          var res = document.getElementById('ikt-filter-res').value;
          var multiplex = document.getElementById('ikt-filter-multiplex').value;
          var status = document.getElementById('ikt-filter-status').value;
          var hemisphere = document.getElementById('ikt-filter-hemisphere').value;
          var aperture = document.getElementById('ikt-filter-aperture').value;
          var filters = [instr, wl, res, multiplex, status, hemisphere, aperture].filter(Boolean);

          function matches(tokenStr, slug) {
            var tokens = ' ' + tokenStr + ' ';
            return filters.every(function (f) { return tokens.indexOf(' ' + f + ' ') !== -1; })
              && matchesSearch(slug);
          }

          document.querySelectorAll('.ikt-row').forEach(function (row) {
            setVisible(row, matches(row.getAttribute('data-tokens'), row.querySelector('.ikt-title-link').getAttribute('data-slug')));
          });
          document.querySelectorAll('.ikt-card').forEach(function (card) {
            setVisible(card, matches(card.className, slugOfCard(card)));
          });
          document.querySelectorAll('.ikt-map-marker').forEach(function (marker) {
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
          var card = document.querySelector('.ikt-card.slug-' + CSS.escape(slug));
          if (!card) { return; }
          card.scrollIntoView({ behavior: 'smooth', block: 'start' });
          card.classList.add('ikt-highlight');
          setTimeout(function () { card.classList.remove('ikt-highlight'); }, 1500);
        }

        document.querySelectorAll('.ikt-title-link').forEach(function (link) {
          link.addEventListener('click', function () { scrollToCard(link.getAttribute('data-slug')); });
        });
        document.querySelectorAll('.ikt-map-marker').forEach(function (marker) {
          marker.addEventListener('click', function () { scrollToCard(marker.getAttribute('data-slug')); });
        });

        var sortState = {};
        document.querySelectorAll('#ikt-telescopes-table th[data-sort]').forEach(function (th) {
          th.addEventListener('click', function () {
            var key = th.getAttribute('data-sort');
            var tbody = document.querySelector('#ikt-telescopes-table tbody');
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

      {% for t in telescopes %}
      .. grid-item-card:: {{ t.facility }}
          :class-item: ikt-card slug-{{ t.slug }} {{ t.filter_tokens }}

          .. _{{ t.slug }}:

          {{ t.aperture or 'TBA' }} — {{ [t.site, t.country] | select | join(', ') }}
          ^^^
          {% for v in (t.instrumentation or []) %}:bdg-light:`{{ v }}` {% endfor %}{% for v in (t.wavelength_regime or []) %}:bdg-light:`{{ v }}` {% endfor %}{% if t.aeon %}:bdg-success:`AEON` {% endif %}{% if t.too_capable %}:bdg-success:`ToO` {% endif %}{% if t.multiplex %}:bdg-light:`Multiplex` {% endif %}

          {% if t.instrument_names %}**Instruments:** {{ t.instrument_names | join(', ') }}{% endif %}

          **Contribution ID:** {{ t.contribution_ids | join(', ') }}

          **First semester:** {{ t.first_semester or 'TBA' }}    **Time available:** {{ t.time_available or 'TBA' }}    **Duration:** {{ t.duration or 'TBA' }}

          {{ t.summary or '' }}

          {% if t.contacts %}**Contact:** {% for c in t.contacts %}{{ c.name }} (`{{ c.email }} <mailto:{{ c.email }}>`_){{ ", " if not loop.last }}{% endfor %}{% endif %}

          {% if t.external_links %}**Links:** {% for link in t.external_links %}`{{ link.label }} <{{ link.url }}>`__{{ ", " if not loop.last }}{% endfor %}{% endif %}

          {% if t.siblings %}
          .. container:: ikt-siblings

             Also available under this contribution: {% for s in t.siblings %}`{{ s.label }} <#{{ s.slug }}>`_{{ ", " if not loop.last }}{% endfor %}
          {% endif %}
          +++
          {% if t.status == 'available' %}:bdg-success:`Available`{% else %}:bdg-warning:`Future semester`{% endif %}

      {% endfor %}
