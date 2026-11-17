---
layout: page
title: Artigos publicados
permalink: /artigos/
description: Arquivo de artigos publicados pelo 2e Lab Brasil sobre dupla excepcionalidade, neurodiversidade, ciência, família, escola e inclusão.
---

Consulte os conteúdos publicados pelo 2e Lab Brasil. A lista é atualizada automaticamente quando novos artigos são publicados.

{% assign published_posts = site.posts | sort: "date" | reverse %}
{% if published_posts.size > 0 %}
<ul class="post-list">
  {% for post in published_posts %}
  <li>
    <span class="post-meta"><time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%d/%m/%Y" }}</time></span>
    <h2 class="post-list-heading"><a class="post-link" href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></h2>
    {% if post.description %}
    <p>{{ post.description | escape }}</p>
    {% elsif post.excerpt %}
    <p>{{ post.excerpt | strip_html | normalize_whitespace | truncate: 220 }}</p>
    {% endif %}
    {% if post.categories and post.categories.size > 0 %}
    <p class="post-meta">Temas: {{ post.categories | join: ", " | replace: "-", " " }}</p>
    {% endif %}
  </li>
  {% endfor %}
</ul>
{% else %}
<p>O primeiro artigo será listado aqui assim que for publicado.</p>
{% endif %}
