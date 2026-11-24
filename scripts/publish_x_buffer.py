#!/usr/bin/env python3
"""Publica no X, via Buffer, o artigo publicado mais recente ainda não divulgado."""
import json
import os
import re
import sys
import urllib.request
from datetime import date
from urllib.error import HTTPError, URLError

REPO = "inforeincluder/re-includer-lab"
SITE = "https://inforeincluder.github.io/re-includer-lab"
API = "https://api.buffer.com"
TOKEN = os.environ["BUFFER_API_KEY"]
HANDLE = os.environ.get("X_HANDLE", "reincluder3457").lstrip("@")

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
    categories_match = re.search(r"(?m)^categories:\s*\[([^]]+)\]", fm)
    category = ""
    if categories_match:
        category = categories_match.group(1).split(",")[0].strip().strip('"').strip("'")
    explicit = field("permalink")
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", filename[:-3])
    path = explicit.strip("/") if explicit else (f"{category}/{slug}" if category else slug)
    return {
        "title": title,
        "description": description,
        "url": f"{SITE}/{path}/",
        "date": filename[:10],
    }

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
        edges {{ node {{ id text status }} }}
      }}
    }}'''
    existing = gql(query).get("posts", {}).get("edges", [])
    known_texts = [edge.get("node", {}).get("text", "") for edge in existing]
    article = next((a for a in articles if not any(a["url"] in text for text in known_texts)), None)
    if not article:
        print("Nenhum artigo novo para divulgar; evitando duplicata.")
        return

    prefix = f'Novo no 2e Lab Brasil: {article["title"]}\n\n'
    suffix = f'\n\nLeia: {article["url"]}'
    room = 280 - len(prefix) - len(suffix)
    description = article["description"][:max(0, room)].rstrip()
    text = prefix + description + suffix
    if len(text) > 280:
        raise RuntimeError("O texto ultrapassou o limite conservador de 280 caracteres.")
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
