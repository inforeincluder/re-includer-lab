---
layout: page
title: Tags
permalink: /tags/
description: Explore os artigos do 2e Lab Brasil por tags e temas específicos relacionados à neurodiversidade, dupla excepcionalidade, educação, ciência e acessibilidade.
---
As tags conectam artigos de diferentes categorias. Selecione um tema para consultar os conteúdos relacionados.

{% assign sorted_tags = site.tags | sort %}
<ul class="post-list">
{% for tag in sorted_tags %}
  <li><a href="#tag-{{ tag[0] | slugify }}">{{ tag[0] | replace: "-", " " }}</a> <span class="post-meta">({{ tag[1].size }})</span></li>
{% endfor %}
</ul>
{% for tag in sorted_tags %}
<section id="tag-{{ tag[0] | slugify }}">
  <h2>{{ tag[0] | replace: "-", " " | capitalize }}</h2>
  <ul>
  {% for post in tag[1] %}
    <li><a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></li>
  {% endfor %}
  </ul>
</section>
{% endfor %}
<p><a href="{{ '/categorias/' | relative_url }}">Explorar categorias</a></p>
