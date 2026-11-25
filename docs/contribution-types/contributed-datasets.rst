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

      {% if highlights %}
      <div class="ikp-teasers">
        <p class="ikp-teaser-heading">Highlighted</p>
        <ul class="ikp-teaser-list">
          {% for item in highlights %}
          <li class="ikp-teaser"><a class="ikp-teaser-link" href="#{{ item.anchor | e }}">{{ item.title | e }}</a>{% if item.reason %} <span class="ikp-teaser-reason">{{ item.reason | e }}</span>{% endif %}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}

      <div class="ikp-filterbar">
        <label>Data type
          <select id="ikp-filter-dt" data-filter-key="dt">
            <option value="">All</option>
            {% for label, slug in all_data_types %}<option value="dt-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Wavelength
          <select id="ikp-filter-wl" data-filter-key="wl">
            <option value="">All</option>
            {% for label, slug in all_wavelengths %}<option value="wl-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Science keyword (UAT)
          <select id="ikp-filter-uat" data-filter-key="uat">
            <option value="">All</option>
            {% for label, slug in all_uat %}<option value="uat-{{ slug }}">{{ label }}</option>{% endfor %}
          </select>
        </label>
        <label>Status
          <select id="ikp-filter-status" data-filter-key="status">
            <option value="">All</option>
            <option value="status-available">Available</option>
            <option value="status-not-yet-delivered">In progress</option>
          </select>
        </label>
      </div>

      <div class="ikp-actionbar">
        <label for="ikp-search" class="ikp-visually-hidden">Search datasets</label>
        <input type="text" id="ikp-search" placeholder="Search title, description, keywords...">
      </div>

      {# Result count: rendered here so it is right without JS; cards.js updates it as the filters change. The hidden status line below it is what screen readers announce. #}
      <p class="ikp-result-count">Showing {{ datasets | length }} of {{ datasets | length }} datasets</p>
      <p class="ikp-visually-hidden ikp-status" role="status"></p>

      <table class="ikp-datasets-table" id="ikp-datasets-table">
        <thead>
          <tr>
            <th scope="col" data-sort="title"><button type="button" class="ikp-sort-btn">Dataset<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="datatype"><button type="button" class="ikp-sort-btn">Data type<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="wavelength"><button type="button" class="ikp-sort-btn">Wavelength<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="recipient"><button type="button" class="ikp-sort-btn">Primary recipient<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="status"><button type="button" class="ikp-sort-btn">Status<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
            <th scope="col" data-sort="updated"><button type="button" class="ikp-sort-btn">Updated<span class="ikp-sort-arrow" aria-hidden="true"></span></button></th>
          </tr>
        </thead>
        <tbody>
          {% for ds in datasets %}
          <tr class="ikp-row" data-card="{{ ds.anchor }}"{% for key, tokens in ds.filters.items() %} data-filter-{{ key }}="{{ tokens | join(' ') }}"{% endfor %}
              data-title="{{ ds.title }}"
              data-datatype="{{ (ds.form_data.data_type or []) | join(', ') }}"
              data-wavelength="{{ (ds.curated.wavelength_regime or []) | join(', ') }}"
              data-recipient="{{ ds.curated.primary_recipient or '' }}"
              data-status="{{ ds.status }}"
              data-updated="{{ ds.last_updated }}">
            <td><button type="button" class="ikp-title-link">{{ ds.title }} ({{ ds.contribution_id }})</button></td>
            <td>{{ (ds.form_data.data_type or []) | join(', ') or 'TBD' }}</td>
            <td>{{ (ds.curated.wavelength_regime or []) | join(', ') or 'TBD' }}</td>
            <td>{{ ds.curated.primary_recipient or 'TBD' }}</td>
            <td>{% if ds.status == 'available' %}<span class="ikp-badge ikp-badge-success">Available</span>{% else %}<span class="ikp-badge ikp-badge-muted">In progress</span>{% endif %}</td>
            <td>{{ ds.last_updated }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <script type="application/json" data-ikp="search-index">{{ search_index_json }}</script>

   .. grid:: 1 1 2 2
      :gutter: 2

      {% for ds in datasets %}
      {% set available = (ds.status == 'available') %}
      .. _{{ ds.anchor }}:

      .. grid-item-card:: {{ ds.title }}
          :class-item: ikp-card

          {{ ds.contribution_id }}{% if ds.display_country %} - {{ ds.display_country }}{% endif %}
          ^^^
          {% for dt in (ds.form_data.data_type or []) %}:bdg-light:`{{ dt }}` {% endfor %}{% for wl in (ds.curated.wavelength_regime or []) %}:bdg-light:`{{ wl }}` {% endfor %}{% for uc in (ds.form_data.uat_category or []) %}:bdg-primary-line:`{{ uc }}` {% endfor %}

          {% if available %}
          {{ ds.curated.summary or 'TBD' }}

          **Primary recipient:** {{ ds.curated.primary_recipient or 'TBD' }}

          **Target audience:** {{ ds.curated.target_audience or ds.form_data.target_audience or 'TBD' }}

          {% if ds.form_data.version %}
          **Version:** {{ ds.form_data.version }}

          {% endif %}
          **Access:** {{ ds.form_data.access_url or 'TBD' }}

          **Documentation:** {{ ds.form_data.tutorials_docs or 'TBD' }}

          **Support channel:** {{ ds.form_data.support_channel or 'TBD' }}

          .. container:: ikp-more-fields

             **Data volume:** {{ ds.form_data.data_volume or 'TBD' }}

             **Hosting location:** {{ ds.form_data.hosting_location or 'TBD' }}

             **Citation:** {{ ds.form_data.citation or 'TBD' }}

             **Maintenance plan:** {{ ds.form_data.maintenance_plan or 'TBD' }}

             **Data schema:** {{ ds.form_data.data_schema_link or 'TBD' }}

             **Access mechanisms:** {{ (ds.form_data.access_mechanisms or []) | join(', ') or 'TBD' }}

             **Authentication:** {{ ds.form_data.authentication or 'TBD' }}

             **Generation methods:** {{ ds.form_data.generation_methods or 'TBD' }}

             **Validation & limitations:** {{ ds.form_data.validation_limitations or 'TBD' }}

          .. raw:: html

             <button type="button" class="ikp-more-btn" data-expand-label="Show more details &#9662;" data-collapse-label="Show fewer details &#9652;">Show more details &#9662;</button>
          {% else %}
          {{ ds.curated.summary or 'TBD' }}

          **Primary recipient:** {{ ds.curated.primary_recipient or 'TBD' }}
          {% endif %}

          {% for rel in ds.related %}
          {% if rel.href %}

          .. raw:: html

             <a class="ikp-also-see" href="{{ rel.href }}">Also see: {{ rel.kind }} ({{ rel.contribution_id }}) &rarr;</a>

          {% endif %}
          {% endfor %}

          *Updated: {{ ds.last_updated }}*
          +++
          {% if available %}:bdg-success:`Available`{% else %}:bdg-muted:`In progress`{% endif %}
      {% endfor %}
