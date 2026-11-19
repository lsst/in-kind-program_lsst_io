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
          <select id="ikp-sw-filter-cat" data-filter-key="cat">
            <option value="">All</option>
            {% for label, slug in all_categories %}<option value="cat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>UAT keyword
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
            <option value="status-delivered">Delivered</option>
            <option value="status-pending">In Progress</option>
          </select>
        </label>
      </div>

      <div class="ikp-actionbar">
        <input type="text" id="ikp-sw-search" placeholder="Search title, description, keywords...">
      </div>

      <table class="ikp-sw-table" id="ikp-sw-table">
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
          <tr class="ikp-row" data-card="{{ item.anchor }}"{% for key, tokens in item.filters.items() %} data-filter-{{ key }}="{{ tokens | join(' ') }}"{% endfor %}
              data-title="{{ item.title }}"
              data-category="{{ item.form_data.category or '' }}"
              data-recipient="{{ item.form_data.primary_recipient_group or '' }}"
              data-status="{{ item.status }}"
              data-updated="{{ item.last_updated or '' }}">
            <td><button type="button" class="ikp-title-link">{{ item.title }} ({{ item.contribution_id }})</button></td>
            <td>{{ item.form_data.category or 'TBD' }}</td>
            <td>{{ item.form_data.primary_recipient_group or 'TBD' }}</td>
            <td>{% if item.status == 'delivered' %}<span class="ikp-badge ikp-badge-success">Delivered</span>{% else %}<span class="ikp-badge ikp-badge-muted">In Progress</span>{% endif %}</td>
            <td>{{ item.last_updated or 'unknown' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script type="application/json" data-ikp="search-index">{{ search_index_json }}</script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for item in software %}
      .. _{{ item.anchor }}:

      .. grid-item-card:: {{ item.title }}
          :class-item: ikp-sw-card ikp-card

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
          {% if rel.href %}

          .. raw:: html

             <a class="ikp-also-see" href="{{ rel.href }}">Also see: {{ rel.kind }} ({{ rel.contribution_id }}) &rarr;</a>

          {% endif %}
          {% endfor %}

          *Updated: {{ item.last_updated or 'unknown' }}*
          +++
          {% if item.status == 'delivered' %}:bdg-success:`Delivered`{% else %}:bdg-muted:`In Progress`{% endif %}
      {% endfor %}
