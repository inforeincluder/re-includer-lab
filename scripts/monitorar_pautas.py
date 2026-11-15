#!/usr/bin/env python3
"""Coleta títulos e resumos de feeds públicos para triagem editorial humana.

Não republica textos, não gera artigos e não publica conteúdo. O relatório serve
apenas como fila de possíveis pautas; cada item deve ser conferido na fonte.
"""
from __future__ import annotations

import argparse
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEEDS = {
    "ScienceDaily — Psychology": "https://www.sciencedaily.com/rss/mind_brain/psychology.xml",
    "ScienceDaily — Mind & Brain": "https://www.sciencedaily.com/rss/mind_brain.xml",
    "ScienceDaily — Health": "https://www.sciencedaily.com/rss/health.xml",
    "The Conversation — Education (UK)": "https://theconversation.com/uk/education/articles.atom",
    "The Conversation — Education (US)": "https://theconversation.com/us/education/articles.atom",
    "The Conversation — Articles": "https://theconversation.com/articles.atom?language=en",
}
KEYWORDS = (
    "autism", "autistic", "adhd", "attention deficit", "neurodiver", "twice-exception",
    "gifted", "high ability", "dyslexia", "dyscalculia", "dyspraxia", "tourette",
    "executive function", "learning disorder", "special education", "inclusive education",
    "child development", "developmental", "mental health", "sensory", "assistive technology",
    "school", "parenting", "anxiety", "intellectual", "creativity", "learning",
)
WINDOW_DAYS = 21
MAX_ITEMS = 35


@dataclass(frozen=True)
class Item:
    source: str
    title: str
    url: str
    summary: str
    published: datetime | None
    score: int


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for child in element:
        if local_name(child.tag) in names:
            return " ".join("".join(child.itertext()).split())
    return ""


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        result = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def extract_link(element: ET.Element) -> str:
    for child in element:
        if local_name(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
            text = (child.text or "").strip()
            if text:
                return text
    return ""


def parse_feed(xml_text: str, source: str, now: datetime | None = None) -> list[Item]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=WINDOW_DAYS)
    root = ET.fromstring(xml_text)
    items: list[Item] = []
    for element in root.iter():
        if local_name(element.tag) not in {"item", "entry"}:
            continue
        title = child_text(element, ("title",))
        summary = child_text(element, ("description", "summary", "content", "encoded"))
        url = extract_link(element)
        date_text = child_text(element, ("pubdate", "published", "updated", "date"))
        published = parse_date(date_text)
        if not title or not url:
            continue
        if published and published < cutoff:
            continue
        haystack = (title + " " + summary).casefold()
        matched = {term for term in KEYWORDS if term in haystack}
        if not matched:
            continue
        clean_summary = html.unescape(re.sub(r"<[^>]+>", " ", summary))
        clean_summary = " ".join(clean_summary.split())[:500]
        items.append(Item(source, title.strip(), url, clean_summary, published, len(matched)))
    return items


def fetch_feed(source: str, url: str, timeout: int = 20) -> list[Item]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "2e-Lab-Brasil-Editorial-Radar/1.0 (+https://inforeincluder.github.io/re-includer-lab/)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        data = response.read(3_000_000)
    return parse_feed(data.decode("utf-8", errors="replace"), source)


def build_report(items: list[Item], failures: list[tuple[str, str]], generated_at: datetime) -> str:
    unique: dict[str, Item] = {}
    for item in items:
        previous = unique.get(item.url)
        if previous is None or item.score > previous.score:
            unique[item.url] = item
    ordered = sorted(
        unique.values(),
        key=lambda x: (x.score, x.published or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )[:MAX_ITEMS]
    lines = [
        "---",
        "layout: page",
        'title: "Radar editorial — candidatos a pauta"',
        "permalink: /radar-editorial/",
        "sitemap: false",
        "---",
        "",
        "# Radar editorial — candidatos a pauta",
        "",
        f"Coletado em: {generated_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        f"Janela: últimos {WINDOW_DAYS} dias. Itens: {len(ordered)}.",
        "",
        "**Uso interno:** esta lista não é uma recomendação de publicação. Abra a fonte, confira data, autoria, estudo original, contexto e limitações. Não traduza nem reproduza o texto do feed.",
        "",
    ]
    if not ordered:
        lines += ["Nenhum item passou pelos filtros nesta execução.", ""]
    for index, item in enumerate(ordered, 1):
        date = item.published.strftime("%Y-%m-%d") if item.published else "data não informada"
        lines += [
            f"## {index}. {item.title}",
            "",
            f"- Fonte: {item.source}",
            f"- Data: {date}",
            f"- Afinidade temática (termos encontrados): {item.score}",
            f"- Link: {item.url}",
        ]
        if item.summary:
            lines += [f"- Resumo do feed: {item.summary}"]
        lines.append("")
    if failures:
        lines += ["## Feeds indisponíveis nesta execução", ""]
        lines += [f"- {source}: {reason}" for source, reason in failures]
        lines.append("")
    lines += [
        "## Checklist de triagem humana",
        "",
        "- [ ] A publicação original foi aberta e sua data confirmada.",
        "- [ ] Autoria, instituição e natureza da fonte foram verificadas.",
        "- [ ] A fonte primária ou documento original foi localizado.",
        "- [ ] O interesse para pessoas neurodivergentes, famílias ou escolas está claro.",
        "- [ ] A pauta permite análise original e uma ferramenta ou ação prática segura.",
        "- [ ] Limitações, incertezas e contexto brasileiro foram identificados.",
        "- [ ] Direitos autorais e necessidade de atribuição foram respeitados.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="radar-pautas.md")
    args = parser.parse_args()
    items: list[Item] = []
    failures: list[tuple[str, str]] = []
    for source, url in FEEDS.items():
        try:
            items.extend(fetch_feed(source, url))
        except Exception as exc:  # feed externo pode falhar sem interromper os demais
            failures.append((source, f"{type(exc).__name__}: {exc}"))
    report = build_report(items, failures, datetime.now(timezone.utc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Relatório salvo em {output}; itens: {len(items)}; feeds com falha: {len(failures)}")
    return 0 if items or not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
