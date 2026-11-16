#!/usr/bin/env python3
"""Validate local links and asset references in a built Jekyll site."""
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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in ("id", "name"):
            if values.get(key):
                self.ids.add(values[key] or "")
        for key in ("href", "src", "action"):
            value = values.get(key)
            if value:
                self.references.append((key, value))


def load_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser


def resolve_local(raw: str, source: Path, site: Path, baseurl: str) -> tuple[Path | None, str]:
    parts = urlsplit(raw.strip())
    if parts.scheme or parts.netloc or raw.startswith("//"):
        return None, ""
    if parts.path.startswith(baseurl + "/") or parts.path == baseurl:
        path_part = parts.path[len(baseurl):]
    else:
        path_part = parts.path
    decoded = unquote(path_part)
    if decoded.startswith("/"):
        candidate = site / decoded.lstrip("/")
    elif decoded:
        candidate = (source.parent / decoded).resolve()
    else:
        candidate = source
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


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: check_site.py DIRETORIO_SITE [BASEURL]")
        return 2
    site = Path(sys.argv[1]).resolve()
    baseurl = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else ""
    if not site.is_dir():
        print(f"Diretório do site não encontrado: {site}")
        return 2

    pages = sorted(site.rglob("*.html"))
    parsed = {page: load_page(page) for page in pages}
    errors: list[str] = []
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
                if destination is None:
                    destination = load_page(target)
                if fragment not in destination.ids:
                    errors.append(f"{source.relative_to(site)}: âncora inexistente: {raw}")

    print(f"Páginas HTML analisadas: {len(pages)}")
    print(f"Referências locais verificadas: {checked}")
    if errors:
        print(f"Falhas encontradas: {len(errors)}")
        for error in errors:
            print(f" - {error}")
        return 1
    print("Nenhum link ou recurso local quebrado encontrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
