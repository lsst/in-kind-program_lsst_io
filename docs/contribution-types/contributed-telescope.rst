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
        {# A banner that is under review or closed is muted, so the open ones stand out. #}
        <div class="ikp-opp-card ikp-opp-phase-{{ opp.phase | replace('_', '-') }}{% if opp.accent %} ikp-opp-card-{{ opp.accent }}{% endif %}{% if opp.phase in ('in_review', 'closed') %} ikp-opp-card-muted{% endif %}" id="opp-{{ opp.slug }}">
          {# The title is a real level-2 heading, so a screen-reader user can jump from banner to banner. cards.css makes it look like the paragraph it replaced. #}
          <h2 class="ikp-opp-title">{{ opp.title | e }}</h2>
          {# The status line sits under the title and says what the phase means ("Deadline 30 Sep 2026"). It is empty when the record lacks the milestone the phase needs. #}
          {% if opp.status_line %}<p class="ikp-opp-status">{{ opp.status_line | e }}</p>{% endif %}
          {# The summary is deliberately not escaped: it is authored HTML (for example <strong>). Every other field below is plain text and is escaped. #}
          <p>{{ opp.summary }}</p>
          {% if opp.milestones %}
          {# role="list" is explicit because Safari drops the list semantics from a list styled list-style: none. #}
          <ul class="ikp-opp-milestones" role="list">
            {% for m in opp.milestones %}
            {% set m_classes = [] %}
            {% if m.get('approximate') %}{% set _ = m_classes.append('approx') %}{% endif %}
            {% if m.passed %}{% set _ = m_classes.append('passed') %}{% endif %}
            {# "(passed)" and "(approx.)" are real text, so screen readers read them and copy and paste keeps them. A passed milestone shows only "(passed)", even when it is also approximate. There is no whitespace between the label and the span: the approximate span carries its own leading space. #}
            <li{% if m_classes %} class="{{ m_classes | join(' ') }}"{% endif %}><strong>{{ m.date_text | e }}</strong> &mdash; {{ m.label | e }}{% if m.passed %}<span class="ikp-milestone-passed">(passed)</span>{% elif m.get('approximate') %}<span class="ikp-milestone-approx"> (approx.)</span>{% endif %}</li>
            {% endfor %}
          </ul>
          {% endif %}
          <div class="ikp-opp-links">
          {% for link in (opp.links or []) %}
            <a href="{{ link.url | e }}">{{ link.label | e }}</a>
          {% endfor %}
          </div>
          {# Collect the related ids that match a card first, so the line is not shown with nothing after "Related facility:". #}
          {% set related_links = [] %}
          {% for cid in (opp.related_contribution_ids or []) %}
            {% for slug in (cid_to_slugs.get(cid) or []) %}{% set _ = related_links.append((cid, slug)) %}{% endfor %}
          {% endfor %}
          {% if related_links %}
          <p class="ikp-opp-related">
            Related facility:
            {% for cid, slug in related_links %}<a href="#{{ slug }}">{{ cid | e }}</a> {% endfor %}
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
        <label for="ikp-search" class="ikp-visually-hidden">Search facilities</label>
        <input type="text" id="ikp-search" placeholder="Search facilities, sites, instruments...">
      </div>

      {# Result count: rendered here so it is right without JS; cards.js updates it as the filters change. The hidden status line below it is what screen readers announce. #}
      <p class="ikp-result-count">Showing {{ telescopes | length }} of {{ telescopes | length }} facilities</p>
      <p class="ikp-visually-hidden ikp-status" role="status"></p>

      <div class="ikp-map-wrap">
        <svg viewBox="0 0 1000 500" width="100%" height="320" role="img" aria-label="World map of facility locations; the table below lists every facility">
          <rect class="ikp-map-bg" x="0" y="0" width="1000" height="500"></rect>
          {% if world_outline_path %}
          <path class="ikp-map-land" d="{{ world_outline_path }}" stroke-width="0.5"></path>
          {% endif %}
          {% for t in telescopes %}
          {% if t.marker_x is not none %}
          {# A marker keeps data-slug as its stable name; data-card is the id the script looks the card up by.
             The status class picks the marker colour in cards.css. The <title> is the tooltip a mouse user
             sees on hover (the map is one image to a screen reader, so it is not read out). It names the
             facility and its site, like the table's Facility and Location columns, then the status, worded
             like the table badges. #}
          {# One shape per status, so colour is not the only cue: Available is a filled circle, Future semester
             a ring (circle, no fill, a 3-wide coloured outline, so its outer edge is the same size as the dot's)
             and Past opportunity a square. All three are centred on the same point (marker_x, marker_y). The
             status class sets the colour in cards.css; the ring class makes that colour an outline instead of a
             fill. Anything that is not Available or Past opportunity is drawn as the Future semester ring. #}
          {% set marker_attributes %}data-slug="{{ t.slug }}" data-card="{{ t.slug }}"{% for key, tokens in t.filters.items() %} data-filter-{{ key }}="{{ tokens | join(' ') }}"{% endfor %}{% endset %}
          {% if t.status == 'available' %}
          {% set status_label = 'Available' %}
          <circle class="ikp-map-marker ikp-map-marker-available" {{ marker_attributes }}
                  cx="{{ t.marker_x }}" cy="{{ t.marker_y }}" r="6"><title>{{ t.facility | e }}{% if t.site %}, {{ t.site | e }}{% endif %}: {{ status_label }}</title></circle>
          {% elif t.status == 'past_opportunity' %}
          {% set status_label = 'Past opportunity' %}
          {# Marker positions are already rounded to 1 decimal in ikp_data/derive.py; round(2) only strips the
             floating-point noise the subtraction adds (444.3 - 5 would print as 439.3 followed by a long tail). #}
          <rect class="ikp-map-marker ikp-map-marker-past" {{ marker_attributes }}
                x="{{ (t.marker_x - 5) | round(2) }}" y="{{ (t.marker_y - 5) | round(2) }}" width="10" height="10"><title>{{ t.facility | e }}{% if t.site %}, {{ t.site | e }}{% endif %}: {{ status_label }}</title></rect>
          {% else %}
          {% set status_label = 'Future semester' %}
          <circle class="ikp-map-marker ikp-map-marker-ring ikp-map-marker-future" {{ marker_attributes }}
                  cx="{{ t.marker_x }}" cy="{{ t.marker_y }}" r="4.5"><title>{{ t.facility | e }}{% if t.site %}, {{ t.site | e }}{% endif %}: {{ status_label }}</title></circle>
          {% endif %}
          {% endif %}
          {% endfor %}
        </svg>
        {# The map key. Its symbols are decoration for the text beside them, so they are hidden from screen
           readers. They carry the status colour classes only: the script treats anything with the
           ikp-map-marker class as a clickable, filterable marker, and these must not be. The key does not
           change when the filters change. Same order as the Status filter. role="list" is explicit because
           Safari drops the list semantics (and with them the name) from a list styled list-style: none. #}
        <ul class="ikp-map-legend" role="list" aria-label="Map key">
          <li><svg class="ikp-map-legend-symbol" viewBox="0 0 12 12" aria-hidden="true" focusable="false"><circle class="ikp-map-marker-available" cx="6" cy="6" r="6"></circle></svg>Available</li>
          <li><svg class="ikp-map-legend-symbol" viewBox="0 0 12 12" aria-hidden="true" focusable="false"><circle class="ikp-map-marker-ring ikp-map-marker-future" cx="6" cy="6" r="4.5"></circle></svg>Future semester</li>
          <li><svg class="ikp-map-legend-symbol" viewBox="0 0 12 12" aria-hidden="true" focusable="false"><rect class="ikp-map-marker-past" x="1" y="1" width="10" height="10"></rect></svg>Past opportunity</li>
        </ul>
      </div>

      <table class="ikp-telescopes-table" id="ikp-telescopes-table">
        <thead>
          <tr>
            <th scope="col" data-sort="facility"><button type="button" class="ikp-sort-btn">Facility<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="location"><button type="button" class="ikp-sort-btn">Location<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="instrumentation"><button type="button" class="ikp-sort-btn">Instrumentation<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="status"><button type="button" class="ikp-sort-btn">Status<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="aperture-value" data-sort-type="number"><button type="button" class="ikp-sort-btn">Aperture<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
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
            <td>{{ (t.instrumentation or []) | join(', ') or 'TBD' }}</td>
            <td>{% if t.status == 'available' %}<span class="ikp-badge ikp-badge-spaced ikp-badge-success">Available</span>{% elif t.status == 'past_opportunity' %}<span class="ikp-badge ikp-badge-spaced ikp-badge-danger">Past opportunity</span>{% else %}<span class="ikp-badge ikp-badge-spaced ikp-badge-warning">Future semester</span>{% endif %}</td>
            <td>{{ t.aperture or 'TBD' }}</td>
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

          {{ t.contribution_ids | select | join(', ') }} · {{ t.aperture or 'TBD' }} — {{ [t.site, t.country] | select | join(', ') }}
          ^^^
          {% for v in (t.instrumentation or []) %}:bdg-light:`{{ v }}` {% endfor %}{% for v in (t.wavelength_regime or []) %}:bdg-light:`{{ v }}` {% endfor %}{% if t.aeon %}:bdg-success:`AEON` {% endif %}{% if t.too_capable %}:bdg-success:`ToO` {% endif %}{% if t.multiplex %}:bdg-light:`Multiplex` {% endif %}

          {% if t.instrument_names %}**Instruments:** {{ t.instrument_names | join(', ') }}{% endif %}

          {% if t.observing_mode_label %}**Observing mode:** {{ t.observing_mode_label }}{% endif %}

          **First semester:** {{ t.first_semester or 'TBD' }}    **Time available:** {{ t.time_available or 'TBD' }}    **Duration:** {{ t.duration or 'TBD' }}

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
