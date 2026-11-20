################
Telescope Access
################

This page lists the facilities expected to be made available via the Vera C. Rubin Observatory In-kind Program. The information on this page is subject to change. Final information on resources, time availability, and other pertinent information will be provided as part of the `NOIRLab Call for Proposals <https://noirlab.edu/science/observing-noirlab/proposals>`_ each semester. Unless otherwise noted, this time will be made available via the NOIRLab Time Allocation Process.

Use the filters, search, or map below to find facilities relevant to your science case.

Please email the in-kind helpdesk rubin-inkind at noirlab dot edu if you have any questions about contributed telescope access.

.. jinja:: contributed_opportunities

   {% if opportunities %}
   .. raw:: html

      <div class="ikp-opp-row">
      {% for opp in opportunities %}
        <div class="ikp-opp-card{% if opp.accent %} ikp-opp-card-{{ opp.accent }}{% endif %}" id="opp-{{ opp.slug }}">
          <p class="ikp-opp-title">{{ opp.title }}</p>
          <p>{{ opp.summary }}</p>
          {% if opp.milestones %}
          <ul class="ikp-opp-milestones">
            {% for m in opp.milestones %}
            {% set m_classes = [] %}
            {% if m.get('approximate') %}{% set _ = m_classes.append('approx') %}{% endif %}
            {% if m.get('passed') %}{% set _ = m_classes.append('passed') %}{% endif %}
            <li{% if m_classes %} class="{{ m_classes | join(' ') }}"{% endif %}><strong>{{ m.display_date or m.date }}</strong> &mdash; {{ m.label }}</li>
            {% endfor %}
          </ul>
          {% endif %}
          <div class="ikp-opp-links">
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

      <div class="ikp-filterbar">
        <label>Instrumentation
          <select id="ikp-filter-instr" data-filter-key="instr">
            <option value="">All</option>
            {% for label, slug in all_instrumentation %}<option value="instr-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Wavelength
          <select id="ikp-filter-wl" data-filter-key="wl">
            <option value="">All</option>
            {% for label, slug in all_wavelengths %}<option value="wl-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        {% if all_resolution_bins %}
        <label>Resolution
          <select id="ikp-filter-res" data-filter-key="res">
            <option value="">All</option>
            {% for key, label in all_resolution_bins %}<option value="res-{{ key }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        {% endif %}
        <label>Multiplex
          <select id="ikp-filter-multiplex" data-filter-key="multiplex">
            <option value="">All</option>
            <option value="multiplex-yes">Yes</option>
          </select>
        </label>
        <label>Status
          <select id="ikp-filter-status" data-filter-key="status">
            <option value="">All</option>
            <option value="status-available">Available</option>
            <option value="status-future-semester">Future semester</option>
            <option value="status-past-opportunity">Past opportunity</option>
          </select>
        </label>
        <label>Hemisphere
          <select id="ikp-filter-hemisphere" data-filter-key="hemisphere">
            <option value="">All</option>
            <option value="hemisphere-northern">Northern</option>
            <option value="hemisphere-southern">Southern</option>
          </select>
        </label>
        <label>Aperture
          <select id="ikp-filter-aperture" data-filter-key="aperture">
            <option value="">All</option>
            {% for key, label in all_aperture_bands %}<option value="aperture-{{ key }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
      </div>

      <div class="ikp-actionbar ikp-actionbar-spaced">
        <input type="text" id="ikp-search" placeholder="Search facilities, sites, instruments...">
      </div>

      <div class="ikp-map-wrap">
        <svg viewBox="0 0 1000 500" width="100%" height="320" role="img" aria-label="World map showing facility locations">
          <rect x="0" y="0" width="1000" height="500" fill="#eef2f0"></rect>
          {% if world_outline_path %}
          <path d="{{ world_outline_path }}" fill="#d7ded9" stroke="#c3ccc5" stroke-width="0.5"></path>
          {% endif %}
          {% for t in telescopes %}
          {% if t.marker_x is not none %}
          {# A marker keeps data-slug as its stable name; data-card is the id the script looks the card up by. #}
          <circle class="ikp-map-marker" data-slug="{{ t.slug }}" data-card="{{ t.slug }}"{% for key, tokens in t.filters.items() %} data-filter-{{ key }}="{{ tokens | join(' ') }}"{% endfor %}
                  cx="{{ t.marker_x }}" cy="{{ t.marker_y }}" r="6"
                  fill="{{ '#1a5c33' if t.status == 'available' else ('#a12626' if t.status == 'past_opportunity' else '#8a5a00') }}"></circle>
          {% endif %}
          {% endfor %}
        </svg>
      </div>

      <table class="ikp-telescopes-table" id="ikp-telescopes-table">
        <thead>
          <tr>
            <th data-sort="facility">Facility</th>
            <th data-sort="location">Location</th>
            <th data-sort="instrumentation">Instrumentation</th>
            <th data-sort="status">Status</th>
            <th data-sort="aperture-value" data-sort-type="number">Aperture</th>
          </tr>
        </thead>
        <tbody>
          {% for t in telescopes %}
          <tr class="ikp-row" data-card="{{ t.slug }}"{% for key, tokens in t.filters.items() %} data-filter-{{ key }}="{{ tokens | join(' ') }}"{% endfor %}
              data-facility="{{ t.facility }}"
              data-location="{{ [t.site, t.country] | select | join(', ') }}"
              data-instrumentation="{{ (t.instrumentation or []) | join(', ') }}"
              data-status="{{ t.status }}"
              data-aperture-value="{{ t.aperture_value if t.aperture_value is not none else '' }}">
            <td><button type="button" class="ikp-title-link">{{ t.facility }}</button></td>
            <td>{{ [t.site, t.country] | select | join(', ') }}</td>
            <td>{{ (t.instrumentation or []) | join(', ') or 'TBA' }}</td>
            <td>{% if t.status == 'available' %}<span class="ikp-badge ikp-badge-spaced ikp-badge-success">Available</span>{% elif t.status == 'past_opportunity' %}<span class="ikp-badge ikp-badge-spaced ikp-badge-danger">Past opportunity</span>{% else %}<span class="ikp-badge ikp-badge-spaced ikp-badge-warning">Future semester</span>{% endif %}</td>
            <td>{{ t.aperture or 'TBA' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script type="application/json" data-ikp="search-index">{{ search_index_json }}</script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for t in telescopes %}
      .. grid-item-card:: {{ t.facility }}
          :class-item: ikp-card

          .. _{{ t.slug }}:

          {{ t.contribution_ids | select | join(', ') }} · {{ t.aperture or 'TBA' }} — {{ [t.site, t.country] | select | join(', ') }}
          ^^^
          {% for v in (t.instrumentation or []) %}:bdg-light:`{{ v }}` {% endfor %}{% for v in (t.wavelength_regime or []) %}:bdg-light:`{{ v }}` {% endfor %}{% if t.aeon %}:bdg-success:`AEON` {% endif %}{% if t.too_capable %}:bdg-success:`ToO` {% endif %}{% if t.multiplex %}:bdg-light:`Multiplex` {% endif %}

          {% if t.instrument_names %}**Instruments:** {{ t.instrument_names | join(', ') }}{% endif %}

          {% if t.observing_mode_label %}**Observing mode:** {{ t.observing_mode_label }}{% endif %}

          **First semester:** {{ t.first_semester or 'TBA' }}    **Time available:** {{ t.time_available or 'TBA' }}    **Duration:** {{ t.duration or 'TBA' }}

          {{ t.summary or '' }}

          {% if t.contacts %}**Contact:** {% for c in t.contacts %}{{ c.name }} (`{{ c.email }} <mailto:{{ c.email }}>`_){% if c.note_rst %} — {{ c.note_rst }}{% endif %}{{ ("; " if t.contacts | selectattr('note_rst') | list else ", ") if not loop.last }}{% endfor %}{% else %}Questions: email the in-kind helpdesk (see the top of this page).{% endif %}

          {% if t.has_separate_process %}Proposals for this facility follow a separate process from the NOIRLab call; see the facility links.{% endif %}

          {% if t.external_links %}**Links:** {% for link in t.external_links %}`{{ link.label }} <{{ link.url }}>`__{{ ", " if not loop.last }}{% endfor %}{% endif %}

          {% if t.siblings %}
          .. container:: ikp-siblings

             Also available under this contribution: {% for s in t.siblings %}`{{ s.label }} <#{{ s.slug }}>`_{{ ", " if not loop.last }}{% endfor %}
          {% endif %}
          +++
          {% if t.status == 'available' %}:bdg-success:`Available`{% elif t.status == 'past_opportunity' %}:bdg-danger:`Past opportunity`{% else %}:bdg-warning:`Future semester`{% endif %}

      {% endfor %}
