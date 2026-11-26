---
layout: plates
permalink: /
title: Home
description: Tristan Buckmaster, Professor of Mathematics at NYU Courant. Research in mathematical fluid dynamics, partial differential equations, and wave turbulence.
page_css: home
page_js: highlights
---
{% assign profile = site.data.profile %}
<section class="bound profile" aria-labelledby="name">
  <div class="identity">
    <h1 id="name">{{ profile.name }}</h1>
    <p class="role">{{ profile.role }}</p>
    <div class="intro-grid">
      <p class="research-intro">{{ profile.intro }}</p>
      <p class="support"><strong>Research support</strong> An <a href="{{ profile.funding.career }}">NSF CAREER award</a> supports my work on singularities in fluids. Other support has included an <a href="{{ profile.funding.frg }}">NSF Focused Research Group</a> and the <a href="{{ profile.funding.simons }}">Simons Collaboration on Wave Turbulence</a>.</p>
    </div>
  </div>
  <img class="portrait" src="{{ profile.portrait | relative_url }}" alt="{{ profile.name }} in front of bookshelves" width="690" height="740">
</section>
{% include plates/highlights.html %}
<section class="bound news" id="news" aria-labelledby="news-heading">
  <h2 class="section-title" id="news-heading">What’s new</h2>
  <ul>
    {% assign ordered_updates = site.data.updates | sort: 'date' | reverse %}
    {% for item in ordered_updates %}
      <li>
        <time datetime="{{ item.date }}">{{ item.date | date: '%-d %b %Y' }}</time>
        <div><a class="entry-title" href="{{ item.url }}">{{ item.title | escape }}</a>{% include plates/paper-mark.html key=item.paper_key %}{% if item.note %}<p class="entry-note">{{ item.note | escape }}</p>{% endif %}</div>
        <span class="entry-kind">{{ item.kind | escape }}</span>
      </li>
    {% endfor %}
  </ul>
</section>
