---
layout: page
title: Tags
permalink: /tags/
description: Explore os artigos do 2e Lab Brasil por tags e temas específicos relacionados à neurodiversidade, dupla excepcionalidade, educação, ciência e acessibilidade.
---
As tags conectam artigos de diferentes categorias. Os temas abaixo indicam os assuntos abordados nos conteúdos publicados.

<ul class="post-list">
{% assign sorted_tags = site.tags | sort %}
{% for tag in sorted_tags %}
  <li><span class="post-link">{{ tag[0] | replace: "-", " " | capitalize }}</span> <span class="post-meta">({{ tag[1].size }} artigo(s))</span>
    <ul>
      {% for post in tag[1] %}
      <li><a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></li>
      {% endfor %}
    </ul>
  </li>
{% endfor %}
</ul>
<p>Explore também as <a href="{{ '/categorias/' | relative_url }}">categorias editoriais</a>.</p>
