#!/usr/bin/env python3
"""Validate links, anchors, assets and basic structure in a built Jekyll site."""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []
        self.ids: set[str] = set()
        self.issues: list[str] = []
        self.lang: str | None = None
        self.title_seen = False
        self.accessibility_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if tag == "title":
            self.title_seen = True
        if tag == "img" and "alt" not in values:
            self.issues.append("imagem sem atributo alt")
        for key in ("id", "name"):
            value = values.get(key)
            if value:
                if value in self.ids:
                    self.issues.append(f"ID duplicado: {value}")
                self.ids.add(value)
        if tag == "script" and values.get("src", "").endswith("/assets/js/accessibility.js"):
            self.accessibility_script = True
        for key in ("href", "src", "action"):
            value = values.get(key)
            if value:
                self.references.append((key, value))


def load_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser


def resolve_local(raw: str, source: Path, site: Path, baseurl: str) -> tuple[Path | None, str]:
    parts = urlsplit(raw.strip())
    if parts.scheme or parts.netloc or raw.startswith("//"):
        return None, ""
    path_part = parts.path
    base_root = bool(baseurl) and path_part.rstrip("/") == baseurl
    if base_root:
        path_part = "/"
    elif baseurl and path_part.startswith(baseurl + "/"):
        path_part = path_part[len(baseurl):]
    decoded = unquote(path_part)
    if not decoded:
        candidate = source
    elif decoded == "/":
        candidate = site / "index.html"
    elif decoded.startswith("/"):
        candidate = site / decoded.lstrip("/")
    else:
        candidate = (source.parent / decoded).resolve()
    try:
        candidate.relative_to(site.resolve())
    except ValueError:
        return None, parts.fragment
    if candidate.is_dir():
        candidate = candidate / "index.html"
    if not candidate.exists() and not candidate.suffix:
        if (candidate / "index.html").exists():
            candidate = candidate / "index.html"
        elif candidate.with_suffix(".html").exists():
            candidate = candidate.with_suffix(".html")
    return candidate, unquote(parts.fragment)


REQUIRED_PAGES = (
    "index.html",
    "artigos/index.html",
    "categorias/index.html",
    "tags/index.html",
    "sobre/index.html",
    "pesquisa/index.html",
    "ferramentas/index.html",
    "fontes-e-metodologia/index.html",
    "privacidade/index.html",
    "visibilidade-ia/index.html",
    "calendario-editorial/index.html",
    "transparencia-comercial/index.html",
    "dupla-excepcionalidade/dupla-excepcionalidade-brasil-o-que-as-pesquisas-mostram/index.html",
)


def validate_site_structure(site: Path, parsed: dict[Path, PageParser]) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PAGES:
        if not (site / relative).is_file():
            errors.append(f"página essencial ausente: {relative}")
    if not (site / "assets/js/accessibility.js").is_file():
        errors.append("arquivo de acessibilidade ausente: assets/js/accessibility.js")
    if any("_drafts" in path.relative_to(site).parts for path in site.rglob("*.html")):
        errors.append("rascunho encontrado no site publicado")
    for path, parser in parsed.items():
        rel = path.relative_to(site)
        if not parser.lang:
            errors.append(f"{rel}: atributo lang ausente no elemento html")
        if not parser.title_seen:
            errors.append(f"{rel}: elemento title ausente")
        errors.extend(f"{rel}: {issue}" for issue in parser.issues)
    for relative in REQUIRED_PAGES:
        page = site / relative
        if page.is_file():
            parser = parsed.get(page) or load_page(page)
            if not parser.accessibility_script:
                errors.append(f"{relative}: script de acessibilidade não carregado")
    return errors


def check_site(site: Path, baseurl: str = "") -> tuple[int, list[str], int, int]:
    site = site.resolve()
    if not site.is_dir():
        return 2, [f"Diretório do site não encontrado: {site}"], 0, 0
    pages = sorted(site.rglob("*.html"))
    parsed = {page: load_page(page) for page in pages}
    errors = validate_site_structure(site, parsed)
    checked = 0
    for source, parser in parsed.items():
        for kind, raw in parser.references:
            target, fragment = resolve_local(raw, source, site, baseurl)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                errors.append(f"{source.relative_to(site)}: {kind} quebrado: {raw}")
                continue
            if fragment and target.suffix.lower() in {".html", ".htm"}:
                destination = parsed.get(target)
                if destination is None and target.is_file():
                    destination = load_page(target)
                if destination and fragment not in destination.ids:
                    errors.append(f"{source.relative_to(site)}: âncora inexistente: {raw}")
    return (1 if errors else 0), errors, len(pages), checked


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: check_site.py DIRETORIO_SITE [BASEURL]")
        return 2
    baseurl = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else ""
    code, errors, page_count, checked = check_site(Path(sys.argv[1]), baseurl)
    print(f"Páginas HTML analisadas: {page_count}")
    print(f"Referências locais verificadas: {checked}")
    if errors:
        print(f"Falhas encontradas: {len(errors)}")
        for error in errors:
            print(f" - {error}")
        return code
    print("Estrutura, acessibilidade básica, links, âncoras e recursos locais validados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
