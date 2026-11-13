#!/usr/bin/env python3
"""Busca estudos recentes no Europe PMC e cria rascunhos para revisão via Pull Request."""
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(".")
POSTS = ROOT / "_posts"
MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
API_KEY = os.getenv("GEMINI_API_KEY")
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "3"))

TERMS = [
    'TITLE_ABS:(autism OR autistic OR "autism spectrum")',
    'TITLE_ABS:("attention deficit" OR ADHD OR "executive function")',
    'TITLE_ABS:(dyslexia OR dyscalculia OR dyspraxia OR Tourette)',
    'TITLE_ABS:("twice exceptional" OR "giftedness" OR "high ability" OR neurodiversity)',
    'TITLE_ABS:("assistive technology" OR "inclusive education" OR neurodevelopment)',
]

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "2e-Lab-Brasil/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))

def gemini_json(prompt):
    if not API_KEY:
        raise RuntimeError("A variável GEMINI_API_KEY não foi configurada.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:70] or "estudo"

def existing_identifiers():
    identifiers = set()
    if POSTS.exists():
        for path in POSTS.glob("*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in re.findall(r"(?im)^doi:\s*['\"]?([^'\"\s]+)", text):
                identifiers.add(match.lower().replace("https://doi.org/", ""))
            for match in re.findall(r"(?im)^pmid:\s*['\"]?([^'\"\s]+)", text):
                identifiers.add("pmid:" + match.strip("'\"").lower())
    return identifiers

def search_articles():
    end = dt.date.today()
    start = end - dt.timedelta(days=14)
    query = "(" + " OR ".join(TERMS) + f") AND FIRST_PDATE:[{start.isoformat()} TO {end.isoformat()}]"
    params = urllib.parse.urlencode({
        "query": query,
        "format": "json",
        "pageSize": "25",
        "resultType": "core",
        "sort": "FIRST_PDATE_D"
    })
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + params
    data = get_json(url)
    return data.get("resultList", {}).get("result", [])

def make_prompt(article):
    abstract = clean(article.get("abstractText"))
    if len(abstract) < 120:
        return None
    title = clean(article.get("title"))
    authors = clean(article.get("authorString"))
    journal = clean(article.get("journalTitle"))
    year = clean(article.get("firstPublicationDate"))
    doi = clean(article.get("doi"))
    pmid = clean(article.get("pmid"))
    source_url = f"https://doi.org/{doi}" if doi else (
        f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else
        f"https://europepmc.org/article/MED/{article.get('id', '')}"
    )
    prompt = f"""
Você é editor científico do 2e Lab Brasil, portal brasileiro de divulgação científica sobre neurodiversidade, dupla/múltipla excepcionalidade, desenvolvimento, cognição, aprendizagem, saúde mental, educação inclusiva e tecnologia assistiva.

Use SOMENTE os dados bibliográficos e o resumo abaixo. Não invente dados, números, métodos ou conclusões que não estejam no material. Se algo não estiver descrito, escreva "não informado no resumo". Não transforme associação em causalidade. Não faça diagnóstico nem recomendação clínica individual.

Retorne APENAS um objeto JSON válido com estas chaves:
"resumo_acessivel": explicação clara em português brasileiro, sem exagerar conclusões;
"tipo_estudo": desenho do estudo, ou "não informado no resumo";
"populacao_amostra": população e tamanho da amostra, ou "não informado no resumo";
"metodos": síntese dos métodos informados;
"resultados": principais achados, distinguindo resultado de interpretação;
"limitacoes": limitações explicitamente informadas ou "não informado no resumo";
"relevancia": por que o estudo pode interessar ao público do 2e Lab Brasil, sem afirmar que estudou 2e se não estudou;
"cautela": o que não é possível concluir a partir deste resumo;
"classificacao_editorial": uma destas opções: "preliminar", "moderada" ou "hipótese", com justificativa curta;
"termos": lista de 3 a 6 palavras-chave em português.

DADOS DO ARTIGO:
Título: {title}
Autores: {authors}
Periódico: {journal}
Data: {year}
DOI: {doi}
PMID: {pmid}
Resumo original:
{abstract}
"""
    return prompt, source_url, doi, pmid, title, authors, journal, year

def yaml_quote(value):
    return json.dumps(clean(value), ensure_ascii=False)

def main():
    POSTS.mkdir(exist_ok=True)
    seen = existing_identifiers()
    articles = search_articles()
    created = 0
    for article in articles:
        if created >= MAX_ARTICLES:
            break
        doi = clean(article.get("doi")).lower()
        pmid = clean(article.get("pmid")).lower()
        identifier = doi or ("pmid:" + pmid if pmid else clean(article.get("id")).lower())
        if not identifier or identifier in seen:
            continue
        prompt_data = make_prompt(article)
        if not prompt_data:
            continue
        prompt, source_url, doi, pmid, title, authors, journal, year = prompt_data
        try:
            summary = gemini_json(prompt)
        except Exception as exc:
            print(f"Falha ao processar '{title}': {exc}", file=sys.stderr)
            continue
        today = dt.date.today().isoformat()
        post_date = clean(article.get("firstPublicationDate"))[:10] or today
        digest = hashlib.sha1(identifier.encode("utf-8")).hexdigest()[:8]
        filename = f"{post_date}-{slugify(title)}-{digest}.md"
        tags = summary.get("termos", [])
        tag_text = ", ".join(yaml_quote(tag) for tag in tags[:6] if clean(tag))
        content = f'''---
layout: post
title: {yaml_quote(title)}
date: {today}
categories: [pesquisa, neurodiversidade]
tags: [{tag_text}]
authors: {yaml_quote(authors)}
journal: {yaml_quote(journal)}
publication_date: {yaml_quote(year)}
doi: {yaml_quote(doi)}
pmid: {yaml_quote(pmid)}
source_url: {yaml_quote(source_url)}
evidence_level: {yaml_quote(summary.get("classificacao_editorial", "preliminar"))}
editorial_status: "aguardando revisão humana"
---

> **Rascunho editorial — não publicado.** Este texto foi preparado com auxílio de IA a partir do resumo bibliográfico. Confira o artigo original antes de aprovar.

## O que o estudo investigou

{clean(summary.get("resumo_acessivel"))}

## Tipo de estudo

{clean(summary.get("tipo_estudo"))}

## População e amostra

{clean(summary.get("populacao_amostra"))}

## Métodos

{clean(summary.get("metodos"))}

## Principais resultados

{clean(summary.get("resultados"))}

## Limitações

{clean(summary.get("limitacoes"))}

## Relevância para neurodiversidade e 2e

{clean(summary.get("relevancia"))}

## O que não podemos concluir

{clean(summary.get("cautela"))}

## Avaliação editorial da evidência

**Classificação proposta:** {clean(summary.get("classificacao_editorial"))}

## Referência e acesso

{authors} ({year}). *{title}*. {journal}. {("DOI: " + doi) if doi else ("PMID: " + pmid if pmid else "")}

[Consultar publicação original]({source_url})

---

**Revisão humana necessária:** confirmar a referência, conferir métodos e resultados no texto original, validar a classificação da evidência e revisar a redação antes de publicar.
'''
        path = POSTS / filename
        path.write_text(content, encoding="utf-8")
        seen.add(identifier)
        created += 1
        print(f"Rascunho criado: {path}")
    print(f"Total de rascunhos criados: {created}")

if __name__ == "__main__":
    main()
