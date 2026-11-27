---
layout: plates
permalink: /publications/
title: Publications
nav: true
nav_order: 1
page_css: publications
page_js: publications
---

<div class="bound pub-page">
  <header class="pub-heading">
    <h1>Publications</h1>
    <p>Papers, preprints, and my doctoral thesis.</p>
    {% if site.data.slop_papers.size > 0 %}
    <div class="pub-symbol-key" id="slop-key" tabindex="-1"><img src="{{ '/assets/figures/slop-mark.svg' | relative_url }}" width="24" height="20" alt=""> Papers I’ve marked as slop</div>
    {% endif %}
  </header>

  <div class="pub-tools">
    <p class="pub-count" role="status" aria-live="polite"><span data-paper-count>{% bibliography_count %} publications</span></p>
    <div class="pub-search" hidden>
      <label for="paper-search">Search publications</label>
      <input id="paper-search" type="search" placeholder="Title or author" autocapitalize="off" spellcheck="false" aria-controls="publication-list">
    </div>
    <div class="pub-jump" hidden>
      <label for="paper-year">Go to year</label>
      <select id="paper-year"><option value="">Choose year</option></select>
    </div>
  </div>

  <div id="publication-list" class="pub-years">
    {% bibliography --group_by year --group_order descending %}
  </div>
  <div class="pub-empty" hidden>
    <p>No publications match your search.</p>
    <button type="button" data-clear-search>Clear search</button>
  </div>
</div>
