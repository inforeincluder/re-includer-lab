import tempfile
import unittest
from pathlib import Path

from scripts.check_site import check_site, resolve_local


class SiteCheckerSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name)
        (self.site / "index.html").write_text(
            '<html lang="pt-BR"><head><title>Início</title></head>'
            '<body><a id="topo" href="/re-includer-lab/">Início</a>'
            '<img src="/re-includer-lab/assets/test.svg" alt="Teste"></body></html>',
            encoding="utf-8",
        )
        (self.site / "sobre").mkdir()
        (self.site / "sobre/index.html").write_text(
            '<html lang="pt-BR"><head><title>Sobre</title></head>'
            '<body><a href="/re-includer-lab/#topo">Voltar</a></body></html>',
            encoding="utf-8",
        )
        (self.site / "assets").mkdir()
        (self.site / "assets/test.svg").write_text("<svg></svg>", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_baseurl_root_resolves_to_homepage_not_current_page(self):
        source = self.site / "sobre/index.html"
        target, fragment = resolve_local(
            "/re-includer-lab/", source, self.site, "/re-includer-lab"
        )
        self.assertEqual(target, self.site / "index.html")
        self.assertEqual(fragment, "")

    def test_relative_fragment_only_resolves_to_current_page(self):
        source = self.site / "sobre/index.html"
        target, fragment = resolve_local("#secao", source, self.site, "/re-includer-lab")
        self.assertEqual(target, source)
        self.assertEqual(fragment, "secao")

    def test_external_links_are_not_checked_as_local_files(self):
        source = self.site / "index.html"
        target, _ = resolve_local("https://example.org/path", source, self.site, "")
        self.assertIsNone(target)

    def test_path_traversal_is_not_resolved_outside_site(self):
        source = self.site / "index.html"
        target, _ = resolve_local("../../outside.html", source, self.site, "")
        self.assertIsNone(target)

    def test_broken_local_link_is_reported(self):
        (self.site / "index.html").write_text(
            '<html lang="pt-BR"><head><title>Início</title></head>'
            '<body><a href="/arquivo-inexistente/">Erro</a></body></html>',
            encoding="utf-8",
        )
        code, errors, _, _ = check_site(self.site)
        self.assertEqual(code, 1)
        self.assertTrue(any("quebrado:" in error for error in errors))

    def test_duplicate_ids_are_reported(self):
        (self.site / "index.html").write_text(
            '<html lang="pt-BR"><head><title>Início</title></head>'
            '<body><div id="repetido"></div><div id="repetido"></div></body></html>',
            encoding="utf-8",
        )
        code, errors, _, _ = check_site(self.site)
        self.assertEqual(code, 1)
        self.assertTrue(any("ID duplicado" in error for error in errors))

    def test_images_without_alt_are_reported(self):
        (self.site / "index.html").write_text(
            '<html lang="pt-BR"><head><title>Início</title></head>'
            '<body><img src="assets/test.svg"></body></html>',
            encoding="utf-8",
        )
        code, errors, _, _ = check_site(self.site)
        self.assertEqual(code, 1)
        self.assertTrue(any("sem atributo alt" in error for error in errors))

    def test_missing_anchor_is_reported(self):
        (self.site / "sobre/index.html").write_text(
            '<html lang="pt-BR"><head><title>Sobre</title></head>'
            '<body><a href="/re-includer-lab/#nao-existe">Ir</a></body></html>',
            encoding="utf-8",
        )
        code, errors, _, _ = check_site(self.site, "/re-includer-lab")
        self.assertEqual(code, 1)
        self.assertTrue(any("âncora inexistente" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
