#!/usr/bin/env python3
"""Publica ou atualiza no Buffer a divulgação do artigo publicado mais recente."""
import json
import os
import re
import unicodedata
import urllib.request
from datetime import date
from urllib.error import HTTPError, URLError

REPO = "inforeincluder/re-includer-lab"
SITE = "https://inforeincluder.github.io/re-includer-lab"
API = "https://api.buffer.com"
TOKEN = os.environ["BUFFER_API_KEY"]
HANDLE = os.environ.get("X_HANDLE", "2eLabBrasil").lstrip("@")

def request_json(url, payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Falha de rede: {exc}") from exc

def gql(query):
    result = request_json(API, {"query": query}, {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    })
    if result.get("errors"):
        raise RuntimeError("Buffer GraphQL: " + json.dumps(result["errors"], ensure_ascii=False))
    return result.get("data") or {}

def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value

def parse_article(raw, filename):
    front = raw.split("---", 2)
    if len(front) < 3:
        return None
    fm = front[1]
    def field(name):
        m = re.search(r"(?m)^" + re.escape(name) + r":\s*(.+?)\s*$", fm)
        return unquote(m.group(1)) if m else ""
    title = field("title")
    description = field("description")
    status = field("review_status")
    if not title or status != "publicado":
        return None
    def yaml_list(name):
        match = re.search(r"(?m)^" + re.escape(name) + r":\s*\[([^\]]*)\]", fm)
        if not match:
            return []
        values = []
        for token in re.findall(r"""["\']([^"\']+)["\']|([^,]+)""", match.group(1)):
            value = (token[0] or token[1]).strip()
            if value:
                values.append(unquote(value))
        return values

    categories = yaml_list("categories")
    tags = yaml_list("tags")
    category = categories[0] if categories else ""
    explicit = field("permalink")
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", filename[:-3])
    path = explicit.strip("/") if explicit else (f"{category}/{slug}" if category else slug)
    return {
        "title": title,
        "description": description,
        "categories": categories,
        "tags": tags,
        "url": f"{SITE}/{path}/",
        "date": filename[:10],
    }

def hashtag(slug):
    normalized = unicodedata.normalize('NFKD', slug)
    ascii_text = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    words = [word for word in re.split(r'[^A-Za-z0-9]+', ascii_text) if word]
    return '#' + ''.join(word[:1].upper() + word[1:] for word in words)

def article_hashtags(article):
    ordered = article.get('categories', []) + article.get('tags', [])
    result, seen = [], set()
    for value in ordered:
        tag = hashtag(value)
        if tag.lower() not in seen:
            seen.add(tag.lower())
            result.append(tag)
        if len(result) == 3:
            break
    return ' '.join(result)

def build_text(article):
    hashtags = article_hashtags(article)
    prefix = f'Novo no 2e Lab Brasil: {article["title"]}\n\n'
    suffix = f'\n\nLeia: {article["url"]}' + (f'\n\n{hashtags}' if hashtags else '')
    room = 280 - len(prefix) - len(suffix)
    description = article['description'][:max(0, room)].rstrip()
    text = prefix + description + suffix
    if len(text) > 280:
        raise RuntimeError('O texto ultrapassou 280 caracteres mesmo após limitar a descrição.')
    return text

def main():
    headers = {"Accept": "application/vnd.github+json"}
    files = request_json(f"https://api.github.com/repos/{REPO}/contents/_posts?ref=main", headers=headers)
    articles = []
    for item in files:
        if item.get("type") != "file" or not item["name"].endswith(".md"):
            continue
        raw_req = urllib.request.Request(item["download_url"], headers={"User-Agent": "2e-lab-social-publisher"})
        with urllib.request.urlopen(raw_req, timeout=30) as response:
            article = parse_article(response.read().decode("utf-8"), item["name"])
        if article and article["date"] <= date.today().isoformat():
            articles.append(article)
    if not articles:
        print("Nenhum artigo com status publicado encontrado.")
        return
    articles.sort(key=lambda x: x["date"], reverse=True)

    orgs = gql("query { account { organizations { id name } } }").get("account", {}).get("organizations", [])
    if not orgs:
        raise RuntimeError("A chave Buffer foi aceita, mas nenhuma organização foi encontrada.")
    org = orgs[0]
    channels = gql(f'query {{ channels(input: {{ organizationId: "{org["id"]}" }}) {{ id name service }} }}').get("channels", [])
    x_channels = [c for c in channels if str(c.get("service", "")).lower() in ("twitter", "x")]
    if HANDLE:
        matching = [c for c in x_channels if HANDLE.lower() in c.get("name", "").lower()]
        if matching:
            x_channels = matching
    if len(x_channels) != 1:
        raise RuntimeError("Não foi possível identificar um único canal X no Buffer. Canais encontrados: " + json.dumps(x_channels, ensure_ascii=False))
    channel = x_channels[0]

    query = f'''query {{
      posts(first: 100, input: {{
        organizationId: "{org["id"]}",
        filter: {{ status: [scheduled, sent], channelIds: ["{channel["id"]}"] }}
      }}) {{
        edges {{ node {{ id text status dueAt }} }}
      }}
    }}'''
    existing = [edge.get("node", {}) for edge in gql(query).get("posts", {}).get("edges", [])]
    article = next((a for a in articles if any(a["url"] in p.get("text", "") for p in existing)), None)
    if article:
        post = next(p for p in existing if article["url"] in p.get("text", ""))
        if str(post.get("status", "")).lower() in ("sent", "published"):
            print("Artigo já publicado no X; nenhuma alteração realizada.")
            return
        new_text = build_text(article)
        mutation = '''mutation {
          editPost(input: { id: "%s", text: %s }) {
            ... on PostActionSuccess { post { id text status dueAt } }
            ... on MutationError { message }
          }
        }''' % (post["id"], json.dumps(new_text, ensure_ascii=False))
        result = gql(mutation).get("editPost", {})
        if result.get("post"):
            updated = result["post"]
            print(json.dumps({
                "status": "post_agendado_atualizado_com_hashtags",
                "channel": channel.get("name"),
                "article": article["url"],
                "buffer_post_id": updated.get("id"),
                "post_status": updated.get("status"),
                "due_at": updated.get("dueAt"),
                "text": updated.get("text"),
            }, ensure_ascii=False))
            return
        raise RuntimeError("Buffer não confirmou a edição: " + json.dumps(result, ensure_ascii=False))

    article = next((a for a in articles if not any(a["url"] in p.get("text", "") for p in existing)), None)
    if not article:
        print("Nenhum artigo novo para divulgar; evitando duplicata.")
        return
    text = build_text(article)
    mutation = '''mutation {
      createPost(input: {
        text: %s,
        channelId: "%s",
        schedulingType: automatic,
        mode: addToQueue
      }) {
        ... on PostActionSuccess { post { id text dueAt status } }
        ... on MutationError { message }
      }
    }''' % (json.dumps(text, ensure_ascii=False), channel["id"])
    result = gql(mutation).get("createPost", {})
    if result.get("post"):
        post = result["post"]
        print(json.dumps({
            "status": "agendado_no_buffer",
            "channel": channel.get("name"),
            "article": article["url"],
            "buffer_post_id": post.get("id"),
            "due_at": post.get("dueAt"),
            "text": post.get("text"),
        }, ensure_ascii=False))
    else:
        raise RuntimeError("Buffer não confirmou a criação: " + json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
