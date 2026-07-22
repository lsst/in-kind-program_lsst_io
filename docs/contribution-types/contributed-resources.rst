###################
Computing Resources
###################

Independent Data Access Centers (IDACs) and Scientific Processing Centers (SPCs)
One of the goals of the In-Kind Program is to augment the available resources for data- and compute-intensive use cases for the Rubin community.
IDACs and SPCs, following the `guidelines laid out by Rubin Observatory <https://rtn-003.lsst.io/>`_, will provide significant computing, storage, data, and experience for such use cases.

What kinds of contributed computing resources will be available?
================================================================

IDACs and SPCs will collectively provide access to CPUs, data storage, databases, and GPUs.

Who has proposed computing resource contributions?
==================================================

The map, filters, search, and table below list the IDACs and SPCs expected to be active during Rubin Operations.
Click a country in the table, or a marker on the map, to jump to its full profile.

.. jinja:: contributed_idacs

   .. raw:: html

      <style>
        .ikt-filterbar { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; }
        .ikt-filterbar label { font-size: 0.9em; }
        .ikt-actionbar { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }
        .ikt-actionbar input[type="text"] { flex: 1; min-width: 220px; padding: 0.4em 0.6em; border: 1px solid #999; border-radius: 0.3em; font-size: 0.9em; }
        .ikt-map-wrap { margin-bottom: 0.5rem; border-radius: 0.5rem; overflow: hidden; background: #eef2f0; }
        .ikt-map-marker { cursor: pointer; fill-opacity: 0.75; stroke: #ffffff; stroke-width: 0.75; }
        .ikt-map-marker:hover { stroke: #1a1a1a; stroke-width: 1.5; }
        .ikt-legend { display: flex; flex-wrap: wrap; gap: 1.2rem; margin-bottom: 1.5rem; font-size: 0.85em; color: #444; }
        .ikt-legend span { display: inline-flex; align-items: center; gap: 0.4em; }
        .ikt-legend i { width: 0.8em; height: 0.8em; border-radius: 50%; display: inline-block; }
        .ikt-idacs-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        .ikt-idacs-table th, .ikt-idacs-table td { text-align: left; padding: 0.5em 0.75em; border-bottom: 1px solid #ddd; }
        .ikt-idacs-table th { cursor: pointer; user-select: none; white-space: nowrap; }
        .ikt-idacs-table td.num, .ikt-idacs-table th.num { text-align: right; }
        .ikt-title-link { color: inherit; text-decoration: none; cursor: pointer; background: none; border: none; padding: 0; font: inherit; text-align: left; }
        .ikt-title-link:hover { text-decoration: underline; }
        .ikt-card.ikt-highlight .sd-card { outline: 3px solid #1f4f8b; outline-offset: 2px; transition: outline-color 1.2s ease; }
      </style>

      <div class="ikt-filterbar">
        <label>Type
          <select id="ikt-filter-type">
            <option value="">All</option>
            {% for v in all_types %}<option value="type-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>Data product
          <select id="ikt-filter-product">
            <option value="">All</option>
            {% for v in all_products %}<option value="product-{{ slugify(v) }}">{{ v }}</option>{% endfor %}
          </select>
        </label>
        <label>GPUs
          <select id="ikt-filter-gpu">
            <option value="">All</option>
            <option value="has-gpu">Offers GPUs</option>
          </select>
        </label>
      </div>

      <div class="ikt-actionbar">
        <input type="text" id="ikt-search" placeholder="Search countries, institutions, software, use cases...">
      </div>

      <div class="ikt-map-wrap">
        <svg viewBox="0 0 1000 500" width="100%" height="360" role="img" aria-label="World map showing IDAC and SPC locations">
          <rect x="0" y="0" width="1000" height="500" fill="#eef2f0"></rect>
          {% if world_outline_path %}
          <path d="{{ world_outline_path }}" fill="#d7ded9" stroke="#c3ccc5" stroke-width="0.5"></path>
          {% endif %}
          {% for t in idacs %}
          {% if t.marker_x is not none %}
          <circle class="ikt-map-marker" data-slug="{{ t.slug }}" data-tokens="{{ t.filter_tokens }}"
                  cx="{{ t.marker_x }}" cy="{{ t.marker_y }}" r="{{ t.marker_r }}"
                  fill="{{ '#1f4f8b' if 'Data Facility' in t.idac_type else ('#1a5c33' if t.idac_type == 'SPC' else '#d35224') }}">
            <title>{{ t.country }} ({{ t.idac_type }})</title>
          </circle>
          {% endif %}
          {% endfor %}
        </svg>
      </div>

      <div class="ikt-legend">
        <span><i style="background:#1f4f8b"></i> Data Facility (Full IDAC)</span>
        <span><i style="background:#d35224"></i> Lite IDAC</span>
        <span><i style="background:#1a5c33"></i> SPC</span>
        <span style="color:#888">Marker size scales with storage commitment</span>
      </div>

      <table class="ikt-idacs-table" id="ikt-idacs-table">
        <thead>
          <tr>
            <th data-sort="country">Country</th>
            <th data-sort="type">Type</th>
            <th data-sort="location">Host</th>
            <th class="num" data-sort="storage">Storage<br><small>PB-yr</small></th>
            <th class="num" data-sort="cpu">CPU<br><small>Mhrs</small></th>
            <th class="num" data-sort="products">Products</th>
          </tr>
        </thead>
        <tbody>
          {% for t in idacs %}
          {% set cap = t.capacity or {} %}
          <tr class="ikt-row" data-tokens="{{ t.filter_tokens }}"
              data-country="{{ t.country }}"
              data-type="{{ t.idac_type }}"
              data-location="{{ t.location.city or '' }}"
              data-storage="{{ cap.storage_pb_years if cap.storage_pb_years is not none else '' }}"
              data-cpu="{{ cap.cpu_mhrs if cap.cpu_mhrs is not none else '' }}"
              data-products="{{ t.product_count }}">
            <td><button type="button" class="ikt-title-link" data-slug="{{ t.slug }}">{{ t.country }}</button></td>
            <td>{{ t.idac_type }}</td>
            <td>{{ t.location.city or 'TBA' }}</td>
            <td class="num">{{ cap.storage_pb_years if cap.storage_pb_years is not none else 'TBD' }}</td>
            <td class="num">{{ cap.cpu_mhrs if cap.cpu_mhrs is not none else 'TBD' }}</td>
            <td class="num">{{ t.product_count }} / {{ t.product_total }}</td>
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
          return (SEARCH_INDEX[slug] || '').indexOf(query) !== -1;
        }

        function setVisible(el, visible) {
          if (visible) { el.style.removeProperty('display'); }
          else { el.style.setProperty('display', 'none', 'important'); }
        }

        function slugOfCard(card) {
          var m = card.className.match(/\bslug-(\S+)/);
          return m ? m[1] : '';
        }

        function applyFilters() {
          var type = document.getElementById('ikt-filter-type').value;
          var product = document.getElementById('ikt-filter-product').value;
          var gpu = document.getElementById('ikt-filter-gpu').value;
          var filters = [type, product, gpu].filter(Boolean);

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

        ['ikt-filter-type', 'ikt-filter-product', 'ikt-filter-gpu'].forEach(function (id) {
          var el = document.getElementById(id);
          if (el) { el.addEventListener('change', applyFilters); }
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

        // Sortable table headers. Numeric columns compare as numbers; blank
        // (TBD) values always sort to the bottom regardless of direction.
        var sortState = {};
        document.querySelectorAll('#ikt-idacs-table th[data-sort]').forEach(function (th) {
          th.addEventListener('click', function () {
            var key = th.getAttribute('data-sort');
            var tbody = document.querySelector('#ikt-idacs-table tbody');
            var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
            var asc = !sortState[key];
            sortState = {};
            sortState[key] = asc;
            rows.sort(function (a, b) {
              var av = a.getAttribute('data-' + key) || '';
              var bv = b.getAttribute('data-' + key) || '';
              if (av === '' && bv !== '') { return 1; }
              if (bv === '' && av !== '') { return -1; }
              var an = parseFloat(av), bn = parseFloat(bv);
              var cmp;
              if (!isNaN(an) && !isNaN(bn)) { cmp = an - bn; }
              else { cmp = av.localeCompare(bv); }
              return asc ? cmp : -cmp;
            });
            rows.forEach(function (r) { tbody.appendChild(r); });
          });
        });
      })();
      </script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for t in idacs %}
      {% set cap = t.capacity or {} %}
      {% set hw = t.hardware or {} %}
      {% set hwparts = [hw.cpu_architecture, hw.gpu_architecture, hw.storage_type, hw.network] | select | list %}
      {% set docs = (t.documentation or []) | selectattr('url') | list %}
      .. grid-item-card:: {{ t.country }}
          :class-item: ikt-card slug-{{ t.slug }} {{ t.filter_tokens }}

          .. _{{ t.slug }}:

          {{ t.idac_type }} — {{ [t.location.city, t.location.institution] | select | join(', ') }}
          ^^^
          {% for p in t.hosted_products %}:bdg-light:`{{ p }}` {% endfor %}{% if cap.gpu_mhrs %}:bdg-success:`GPUs` {% endif %}

          **Capacity (13-yr):** Storage {{ cap.storage_pb_years if cap.storage_pb_years is not none else 'TBD' }} PB-yr · CPU {{ cap.cpu_mhrs if cap.cpu_mhrs is not none else 'TBD' }} Mhrs{% if cap.gpu_mhrs %} · GPU {{ cap.gpu_mhrs }} Mhrs{% endif %}{% if cap.expected_local_users is not none %} · ~{{ cap.expected_local_users }} expected local users{% endif %}

          {% if t.data_releases %}**Data releases:** {% for r in t.data_releases %}:bdg-light:`{{ r }}` {% endfor %}{% endif %}

          {% if hwparts %}**Hardware:** {{ hwparts | join(' · ') }}{% endif %}

          {% if t.software_services %}**Software & services:** {{ t.software_services }}{% endif %}

          {% if t.complementary_datasets %}**Complementary datasets:** {{ t.complementary_datasets }}{% endif %}

          {% if t.use_cases %}**Science use cases:** {{ t.use_cases }}{% endif %}

          {% if t.science_collaboration_agreements %}**Science Collaboration agreements:** {{ t.science_collaboration_agreements }}{% endif %}

          {% if docs %}**Documentation:** {% for d in docs %}`{{ d.title or d.url }} <{{ d.url }}>`__{{ ", " if not loop.last }}{% endfor %}{% endif %}

          {% if t.contacts %}**Contacts:** {% for c in t.contacts %}{{ c.name }}{% if c.email %} (`{{ c.email }} <mailto:{{ c.email }}>`_){% endif %}{{ ", " if not loop.last }}{% endfor %}{% endif %}

          {% if t.notes %}**Notes:** {{ t.notes }}{% endif %}
          +++
          {% if 'Data Facility' in t.idac_type %}:bdg-primary:`{{ t.idac_type }}`{% elif t.idac_type == 'SPC' %}:bdg-success:`SPC`{% else %}:bdg-secondary:`{{ t.idac_type }}`{% endif %} :bdg-light:`{{ t.product_count }} / {{ t.product_total }} data products`

      {% endfor %}

What data and services will be available?
=========================================

The profiles above are built from the same underlying data as
`this spreadsheet <https://docs.google.com/spreadsheets/d/1r6JH0_5ROdSZ7I9_N4eSEHGbYgOO2QOwW_70IGo8RSg/edit?usp=sharing>`_,
which reflects the current plans for the Rubin data, services, and potential use cases to be
supported at individual IDACs.

What are some potential uses of contributed computing resources?
================================================================

The virtual workshop `Supporting Computational Science with Rubin LSST <https://project.lsst.org/meetings/rubin-idacs/welcome>`_, held in March 2023, featured discussion of a significant number of use cases submitted by members of the science community.
Links to the use cases, presentations, recordings, notes, and background material are available on the `workshop web page <https://project.lsst.org/meetings/rubin-idacs/documents>`_.

IDACs are considering a range of specific use cases, including time series analyses, solar system occultation predictions, and development of photometric redshift training sets, as well as general use.
IDACs are also following the development of the use cases identified in the workshop `"From Data to Software to Science with the Rubin Observatory LSST" <https://arxiv.org/pdf/2208.02781>`_,
and may adopt some of these as a basis for specific datasets and services.

When will IDACs and SPCs be available to the community?
=======================================================

As seen in `this presentation <https://docs.google.com/presentation/d/1wCmsvOX87JjOP5lFVBNoMtCzm9Me7EndUhJdmz7kJKE/edit?usp=sharing>`_, IDACs and SPCs are expected to start operations with the release of LSST DR1 sometime in 2026.

Want to know more?
==================
The IDACs Coordination Group maintains a `space on Community <https://community.lsst.org/c/sci/idacs/44>`_ for discussion and sharing knowledge amongst IDACs and SPCs and their user communities. Join the conversation!
