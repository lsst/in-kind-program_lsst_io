########
Software
########

The Vera C. Rubin Observatory In-Kind Program includes contributed software: directable and non-directable software-development effort that international partners contribute to Rubin teams and LSST Science Collaborations.
This page lists all current software-development contributions. General pool contributions -- directable effort offered without a recipient defined ahead of time -- are listed on the :doc:`general-pool` page instead.

Use the filters or the table below to browse by category, science keyword, or recipient group.
Each entry starts with the basics from the original proposal; cards marked *Available* have a full team-submitted record on file, and cards marked *In progress* are still awaiting that submission.
Some software contributions also produce a dataset -- where that's the case, the card links to the matching entry on the :doc:`contributed-datasets` page.

Please email the in-kind helpdesk rubin-inkind at noirlab dot edu if you have any questions about contributed software.

.. jinja:: contributed_software

   .. raw:: html

      {% if highlights %}
      <div class="ikp-teasers">
        <p class="ikp-teaser-heading" id="ikp-teasers-heading">Highlighted</p>
        {# aria-labelledby names the list after the visible label. role="list" is explicit because Safari drops the list semantics (and with them the name) from a list styled list-style: none. #}
        <ul class="ikp-teaser-list" role="list" aria-labelledby="ikp-teasers-heading">
          {% for item in highlights %}
          <li class="ikp-teaser"><a class="ikp-teaser-link" href="#{{ item.anchor | e }}">{{ item.title | e }}</a>{% if item.reason %} <span class="ikp-teaser-reason">{{ item.reason | e }}</span>{% endif %}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}

      <div class="ikp-filterbar">
        <label>Category
          <select id="ikp-sw-filter-cat" data-filter-key="cat">
            <option value="">All</option>
            {% for label, slug in all_categories %}<option value="cat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Science keyword (UAT)
          <select id="ikp-sw-filter-uat" data-filter-key="uat">
            <option value="">All</option>
            {% for label, slug in all_uat %}<option value="uat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Primary recipient
          <select id="ikp-sw-filter-recipient" data-filter-key="recipient">
            <option value="">All</option>
            {% for label, slug in all_recipients %}<option value="recipient-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Status
          <select id="ikp-sw-filter-status" data-filter-key="status">
            <option value="">All</option>
            <option value="status-available">Available</option>
            <option value="status-pending">In progress</option>
          </select>
        </label>
      </div>

      <div class="ikp-actionbar">
        <label for="ikp-sw-search" class="ikp-visually-hidden">Search software</label>
        <input type="text" id="ikp-sw-search" placeholder="Search title, description, keywords...">
      </div>

      {# Result count: rendered here so it is right without JS; cards.js updates it as the filters change. The hidden status line below it is what screen readers announce. #}
      <p class="ikp-result-count">Showing {{ software | length }} of {{ software | length }} software contributions</p>
      <p class="ikp-visually-hidden ikp-status" role="status"></p>

      {# Only the table scrolls sideways on a narrow screen (WCAG 1.4.10); see .ikp-table-scroll in cards.css. #}
      <div class="ikp-table-scroll">
      <table class="ikp-sw-table" id="ikp-sw-table">
        <thead>
          <tr>
            <th scope="col" data-sort="title"><button type="button" class="ikp-sort-btn">Software<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="category"><button type="button" class="ikp-sort-btn">Category<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="recipient"><button type="button" class="ikp-sort-btn">Primary recipient<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="status"><button type="button" class="ikp-sort-btn">Status<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="updated"><button type="button" class="ikp-sort-btn">Updated<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
          </tr>
        </thead>
        <tbody>
          {% for item in software %}
          <tr class="ikp-row" data-card="{{ item.anchor }}"{% for key, tokens in item.filters.items() %} data-filter-{{ key }}="{{ tokens | join(' ') }}"{% endfor %}
              data-title="{{ item.title }}"
              data-category="{{ item.form_data.category or '' }}"
              data-recipient="{{ item.form_data.primary_recipient_group or '' }}"
              data-status="{{ item.status }}"
              data-updated="{{ item.last_updated }}">
            <td><button type="button" class="ikp-title-link">{{ item.title }} ({{ item.contribution_id }})</button></td>
            <td>{{ item.form_data.category or 'TBD' }}</td>
            <td>{{ item.form_data.primary_recipient_group or 'TBD' }}</td>
            <td>{% if item.status == 'available' %}<span class="ikp-badge ikp-badge-success">Available</span>{% else %}<span class="ikp-badge ikp-badge-muted">In progress</span>{% endif %}</td>
            <td>{{ item.last_updated }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      </div>

      <script type="application/json" data-ikp="search-index">{{ search_index_json }}</script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for item in software %}
      .. _{{ item.anchor }}:

      .. grid-item-card:: {{ item.title }}
          :class-item: ikp-sw-card ikp-card

          {{ item.contribution_id }}{% if item.display_country %} - {{ item.display_country }}{% endif %}
          ^^^
          {% for kw in item.uat_keywords %}:bdg-light:`{{ kw }}` {% endfor %}

          **Primary recipient:** {{ item.form_data.primary_recipient_group or 'TBD' }}

          {% if item.form_data.additional_recipient_groups %}**Additional recipients:** {{ item.form_data.additional_recipient_groups | join(', ') }}{% endif %}

          **Category:** {{ item.form_data.category or 'TBD' }}

          {% if item.status == 'available' and item.display_version %}**Version:** {{ item.display_version }}{% endif %}

          {% if item.form_data.software_name %}**Software:** {{ item.form_data.software_name }}{% endif %}

          {% if item.approx_start %}**Start (approx.):** {{ item.approx_start }}{% endif %}

          {% if item.software_links %}**Links:** {% for link in item.software_links %}`{{ link.label }} <{{ link.url }}>`__{{ ", " if not loop.last else "" }}{% endfor %}{% endif %}

          {% if item.documentation_links %}**Documentation:** {% for link in item.documentation_links %}`{{ link.label }} <{{ link.url }}>`__{{ ", " if not loop.last else "" }}{% endfor %}{% endif %}

          {% if item.form_data.support %}**Support:** {{ item.form_data.support }}{% endif %}

          .. raw:: html

             <div class="ikp-desc" id="{{ item.anchor }}-desc">{{ item.description_html }}</div>
             <button type="button" class="ikp-expand-btn" aria-controls="{{ item.anchor }}-desc" aria-expanded="false" hidden data-expand-label="Read full description" data-collapse-label="Show less">Read full description <span aria-hidden="true">&#9662;</span></button>

          {% for rel in item.related %}
          {% if rel.href %}

          .. raw:: html

             <a class="ikp-also-see" href="{{ rel.href }}">Also see: {{ rel.kind }} ({{ rel.contribution_id }}) <span aria-hidden="true">&rarr;</span></a>

          {% endif %}
          {% endfor %}

          *Updated: {{ item.last_updated }}*
          +++
          {% if item.status == 'available' %}:bdg-success:`Available`{% else %}:bdg-muted:`In progress`{% endif %}
      {% endfor %}
