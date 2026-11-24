---
layout: page
title: "Terapia Ocupacional"
permalink: /tags/terapia-ocupacional/
tag: "terapia-ocupacional"
---

{% assign tagged_posts = site.tags[page.tag] %}
{% if tagged_posts and tagged_posts.size > 0 %}
<ul class="post-list">
{% for post in tagged_posts %}
  <li><span class="post-meta">{{ post.date | date: "%d/%m/%Y" }}</span><h3><a class="post-link" href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></h3>{% if post.description %}<p>{{ post.description | escape }}</p>{% endif %}</li>
{% endfor %}
</ul>
{% else %}
<p>Ainda não há artigos associados a esta tag.</p>
{% endif %}
<p><a href="{{ '/tags/' | relative_url }}">Voltar ao índice de tags</a></p>
