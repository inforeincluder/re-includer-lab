import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from scripts import monitorar_estudos as monitor


def sample_article():
    return {
        "abstractText": "Resumo científico suficientemente longo. " * 12,
        "title": 'Título: teste "especial"',
        "authorString": "Pessoa A",
        "journalTitle": "Revista",
        "firstPublicationDate": "2026-10-01",
        "doi": "https://doi.org/10.1234/ABC.",
        "pmid": "123456",
    }


def sample_summary():
    return {
        "resumo_acessivel": "Resumo acessível.",
        "tipo_estudo": "Observacional.",
        "populacao_amostra": "Amostra não informada.",
        "metodos": "Métodos descritos.",
        "resultados": "Resultados descritos.",
        "limitacoes": "Não informadas no resumo.",
        "relevancia": "Pode interessar ao público do portal.",
        "cautela": "Não permite inferir causalidade.",
        "classificacao_editorial": "preliminar — baseada apenas no resumo.",
        "termos": ["educação", "cognição", "inclusão"],
    }


class MonitoramentoTests(unittest.TestCase):
    def test_normalize_doi(self):
        self.assertEqual(
            monitor.normalize_doi("https://doi.org/10.1234/ABC."),
            "10.1234/abc",
        )

    def test_article_identifier_prefers_doi_then_pmid(self):
        self.assertEqual(
            monitor.article_identifier(sample_article()),
            "10.1234/abc",
        )
        self.assertEqual(
            monitor.article_identifier({"pmid": " 123 "}),
            "pmid:123",
        )

    def test_existing_identifiers_reads_drafts_and_posts(self):
        with tempfile.TemporaryDirectory() as temp:
            drafts = Path(temp) / "_drafts"
            posts = Path(temp) / "_posts"
            drafts.mkdir()
            posts.mkdir()
            (drafts / "draft.md").write_text(
                'doi: "https://doi.org/10.1234/ABC"\n', encoding="utf-8"
            )
            (posts / "post.md").write_text(
                "pmid: 456\n", encoding="utf-8"
            )
            self.assertEqual(
                monitor.existing_identifiers(drafts, posts),
                {"10.1234/abc", "pmid:456"},
            )

    def test_validate_summary_rejects_missing_field(self):
        with self.assertRaisesRegex(ValueError, "resumo_acessivel"):
            monitor.validate_summary({})

    def test_validate_summary_rejects_invalid_tags(self):
        summary = sample_summary()
        summary["termos"] = ["apenas uma"]
        with self.assertRaisesRegex(ValueError, "3 a 6"):
            monitor.validate_summary(summary)

    def test_render_draft_uses_drafts_safe_filename_and_human_review(self):
        filename, content = monitor.render_draft(
            sample_article(), sample_summary()
        )
        self.assertTrue(filename.endswith(".md"))
        self.assertIn("aguardando revisão humana", content)
        self.assertIn("Rascunho editorial — não publicado", content)
        self.assertIn("mover este arquivo para `_posts/`", content)
        self.assertEqual(
            content.split("title: ", 1)[1].splitlines()[0],
            '"Título: teste \\"especial\\""',
        )

    @patch.object(monitor.time, "sleep")
    @patch.object(monitor.urllib.request, "urlopen")
    def test_open_with_retry_retries_503_then_returns(self, urlopen, _sleep):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"ok"

        error = urllib.error.HTTPError(
            "https://example.invalid", 503, "busy", {}, None
        )
        urlopen.side_effect = [error, Response()]
        request = monitor.urllib.request.Request("https://example.invalid")
        self.assertEqual(
            monitor.open_with_retry(request, 1, "teste"),
            b"ok",
        )
        self.assertEqual(urlopen.call_count, 2)

    @patch.object(monitor.time, "sleep")
    @patch.object(monitor.urllib.request, "urlopen")
    def test_open_with_retry_fails_after_retry_limit(self, urlopen, _sleep):
        error = urllib.error.HTTPError(
            "https://example.invalid", 503, "busy", {}, None
        )
        urlopen.side_effect = error
        request = monitor.urllib.request.Request("https://example.invalid")
        with self.assertRaises(monitor.TemporaryServiceError):
            monitor.open_with_retry(request, 1, "teste")
        self.assertEqual(urlopen.call_count, monitor.RETRY_ATTEMPTS)

    def test_retry_after_is_bounded(self):
        self.assertEqual(monitor.retry_delay(0, "120"), 60.0)
        self.assertEqual(monitor.retry_delay(0, "0"), 0.0)


if __name__ == "__main__":
    unittest.main()
