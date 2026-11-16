#!/usr/bin/env python3
"""Descobre pautas em fontes públicas por RSS e prepara rascunhos para revisão humana."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from monitorar_estudos import gemini_json, clean, slugify  # noqa: E402

DRAFTS = ROOT / "_drafts"
LOGGER = logging.getLogger("monitorar_fontes_publicas")
MAX_ITEMS = int(os.getenv("MAX_PUBLIC_ITEMS", "2"))
DAYS = int(os.getenv("PUBLIC_LOOKBACK_DAYS", "14"))

# Feeds públicos usados como radar editorial. A notícia é uma pista, não prova científica.
FEEDS = [
    ("ScienceDaily — Autism", "https://www.sciencedaily.com/rss/mind_brain/autism.xml"),
    ("Child Mind Institute", "https://childmind.org/feed/"),
    ("Agência Fiocruz", "https://agencia.fiocruz.br/rss.xml"),
    ("Jornal da USP", "https://jornal.usp.br/feed/"),
    ("The Conversation", "https://theconversation.com/articles.atom"),
]
# A triagem exige sinal temático no TÍTULO para evitar pautas apenas tangencialmente relacionadas.
TITLE_TERMS = (
    "autism", "autistic", "adhd", "attention deficit", "gifted", "giftedness",
    "twice exceptional", "neurodivers", "dyslexia", "dyscalculia", "dyspraxia",
    "tourette", "executive function", "neurodevelopment", "assistive technology",
    "inclusive education", "high abilities", "autismo", "tdah", "altas habilidades",
    "superdot", "dupla excepcionalidade", "dislexia", "discalculia", "dispraxia",
    "funções executivas", "tecnologia assistiva", "educação inclusiva",
    "augmentative communication", "comunicação aumentativa", "special education",
    "educação especial", "learning disability", "sensory processing",
    "processamento sensorial", "disability", "deficiência",
)


def has_topic_title(title: str) -> bool:
    normalized = clean(title).casefold()
    return any(term.casefold() in normalized for term in TITLE_TERMS)


def get_feed(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "2e-Lab-Brasil/1.0 (+https://inforeincluder.github.io/re-includer-lab/)", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()


def strip_html(value: str) -> str:
    value = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", value or "", flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return clean(html.unescape(value))


def parse_date(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            return None


def parse_feed(raw: bytes, source: str) -> list[dict[str, str]]:
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    if not items:
        items = [node for node in root.iter() if node.tag.endswith("entry")]
    output = []
    for item in items:
        def field(*suffixes: str) -> str:
            for child in item:
                if any(child.tag.endswith(suffix) for suffix in suffixes):
                    return clean("".join(child.itertext()))
            return ""
        title = field("title")
        link = field("link")
        if not link:
            for child in item:
                if child.tag.endswith("link"):
                    link = clean(child.attrib.get("href") or child.text)
                    if link:
                        break
        summary = field("description", "summary", "encoded", "content")
        published = field("pubDate", "published", "updated")
        output.append({
            "source": source, "title": title, "url": link,
            "summary": strip_html(summary)[:3500], "published": clean(published),
        })
    return output


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)
    candidates: list[dict[str, str]] = []
    for source, url in FEEDS:
        try:
            rows = parse_feed(get_feed(url), source)
            LOGGER.info("%s: %d itens no feed.", source, len(rows))
        except Exception as exc:  # uma fonte indisponível não interrompe as demais
            LOGGER.warning("%s indisponível: %s", source, exc)
            continue
        for row in rows:
            if not row["title"] or not row["url"] or not has_topic_title(row["title"]):
                LOGGER.info("Ignorado por título sem sinal temático: %s", row["title"])
                continue
            published = parse_date(row["published"])
            if published and published < cutoff:
                continue
            candidates.append(row)

    seen: set[str] = set()
    unique = []
    for row in candidates:
        key = hashlib.sha256(row["url"].encode("utf-8")).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(row)
    unique.sort(key=lambda row: parse_date(row["published"]) or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True)

    existing_content = []
    for folder in (DRAFTS, ROOT / "_posts"):
        if folder.exists():
            for path in folder.glob("*.md"):
                existing_content.append(path.read_text(encoding="utf-8", errors="ignore"))
    made = 0
    for item in unique:
        if made >= MAX_ITEMS:
            break
        if any(item["url"] in content for content in existing_content):
            continue
        prompt = f"""
Você é editor de divulgação científica do 2e Lab Brasil. Crie um rascunho ORIGINAL em português brasileiro, claro e acessível, baseado SOMENTE no material fornecido abaixo.
Não copie nem traduza a matéria. Não invente fatos, números, especialistas, estudos, links, DOI ou citações. A fonte pode ser jornalística ou institucional e NÃO substitui a fonte primária.
Se a matéria não fornecer evidência verificável, trate-a como pauta/relato e sinalize claramente que a alegação precisa ser confirmada. Não dê diagnóstico, tratamento ou aconselhamento médico.
Conecte o assunto a famílias, pessoas neurodivergentes, educadores ou profissionais somente quando houver base no material. Acrescente uma seção "O que sabemos e o que ainda falta verificar", limitações e uma aplicação prática segura que não seja teste diagnóstico.
Entregue JSON com chaves: title, description, category, article_markdown.
O artigo deve ter 700-1000 palavras, título de busca sem sensacionalismo, resposta direta no início, subtítulos, FAQ curto, link para a fonte original e uma nota explícita de revisão humana pendente.
FONTE: {json.dumps(item, ensure_ascii=False)}
"""
        try:
            draft = gemini_json(prompt)
            title = clean(draft.get("title"))[:140]
            body = str(draft.get("article_markdown") or "").strip()
            if not title or len(body) < 900:
                LOGGER.warning("Resposta editorial incompleta para %s.", item["url"])
                continue
            digest = hashlib.sha256(item["url"].encode("utf-8")).hexdigest()[:8]
            filename = f"{dt.date.today().isoformat()}-{slugify(title)}-{digest}.md"
            category = slugify(clean(draft.get("category")) or "neurodiversidade")
            content = (
                "---\nlayout: post\ntitle: " + json.dumps(title, ensure_ascii=False)
                + "\ndate: " + dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
                + "\ncategories: [" + category + "]\ndescription: "
                + json.dumps(clean(draft.get("description"))[:180], ensure_ascii=False)
                + "\neditorial_type: atualidade\nreview_status: revisão humana pendente"
                + "\nmonetization: none\nsource_url: " + json.dumps(item["url"], ensure_ascii=False)
                + "\n---\n\n" + body
                + "\n\n---\n\n**Fonte monitorada:** [" + item["source"] + "](" + item["url"] + ")."
                + "\n\n**Status editorial:** rascunho assistido por IA. Conferir a fonte original, localizar estudos/documentos primários, validar todas as afirmações e revisar humanamente antes de publicar.\n"
            )
            DRAFTS.mkdir(exist_ok=True)
            (DRAFTS / filename).write_text(content, encoding="utf-8")
            existing_content.append(content)
            made += 1
            LOGGER.info("Rascunho criado: %s", filename)
        except Exception as exc:
            LOGGER.warning("Não foi possível preparar pauta %s: %s", item["url"], exc)
    LOGGER.info("Total de rascunhos públicos criados: %d", made)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
