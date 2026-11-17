---
layout: page
title: Tags
permalink: /tags/
description: Explore os artigos do 2e Lab Brasil por tags e temas específicos relacionados à neurodiversidade, dupla excepcionalidade, educação, ciência e acessibilidade.
---
As tags conectam artigos de diferentes categorias. Selecione um tema para consultar os conteúdos relacionados.

<ul class="post-list">
{% assign sorted_tags = site.tags | sort %}
{% for tag in sorted_tags %}
  <li><a class="post-link" href="{{ '/tags/' | append: tag[0] | append: '/' | relative_url }}">{{ tag[0] | replace: "-", " " | capitalize }}</a> <span class="post-meta">({{ tag[1].size }} artigo(s))</span></li>
{% endfor %}
</ul>
<p>Explore também as <a href="{{ '/categorias/' | relative_url }}">categorias editoriais</a>.</p>
