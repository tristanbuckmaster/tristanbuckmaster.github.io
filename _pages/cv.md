---
layout: plates
permalink: /cv/
title: Curriculum vitae
description: Academic appointments, education, selected honors, and the complete curriculum vitae of Tristan Buckmaster.
page_css: cv
---
<div class="bound cv">
  <header class="page-heading">
    <h1>Curriculum vitae</h1>
    <p>{{ site.data.profile.name }} · {{ site.data.cv_overview.updated }}</p>
    <div class="cv-actions">
      <a class="read-cv" href="{{ '/assets/pdf/CV.pdf' | relative_url }}">Read the full CV <small>(PDF)</small></a>
      <a href="{{ '/assets/pdf/CV.pdf' | relative_url }}" download="Tristan-Buckmaster-CV.pdf">Download PDF</a>
    </div>
  </header>
  {% for section in site.data.cv_overview.sections %}
    <section class="cv-section">
      <h2>{{ section.title | escape }}</h2>
      <ul>
        {% for item in section.items %}
          <li>{% if item.date != '' %}<span>{{ item.date | escape }}</span>{% endif %}<p>{{ item.text | escape }}</p></li>
        {% endfor %}
      </ul>
    </section>
  {% endfor %}
</div>
