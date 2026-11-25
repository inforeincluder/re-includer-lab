---
layout: page
title: Categorias
description: "Explore os artigos do 2e Lab Brasil por categoria: dupla excepcionalidade, autismo, TDAH, altas habilidades, educação inclusiva, tecnologia assistiva e mais."
---
Encontre conteúdos organizados por assunto. Cada categoria reúne artigos publicados e é atualizada automaticamente.

<ul class="post-list">
{% for category in site.taxonomy_categories %}
  {% assign category_posts = site.posts | where_exp: "post", "post.categories contains category.slug" %}
  <li>
    <h2 class="post-list-heading">{{ category.name }}</h2>
    <p>{{ category.description }}</p>
    <span class="post-meta">{{ category_posts.size }} artigo(s)</span>
    {% if category_posts.size > 0 %}
    <ul>
      {% for post in category_posts %}
      <li><a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></li>
      {% endfor %}
    </ul>
    {% endif %}
  </li>
{% endfor %}
</ul>
<p>Também é possível explorar os assuntos por <a href="{{ '/tags/' | relative_url }}">tags</a>.</p>
