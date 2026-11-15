import unittest
from datetime import datetime, timezone

from scripts.monitorar_pautas import build_report, parse_feed


class EditorialRadarTests(unittest.TestCase):
    def test_parse_rss_filters_relevant_recent_items(self):
        xml = """<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>New findings on ADHD and executive function</title>
            <link>https://example.org/adhd</link>
            <description>Researchers examine attention and learning.</description>
            <pubDate>Sat, 14 Nov 2026 12:00:00 GMT</pubDate>
          </item>
          <item>
            <title>Old autism study</title>
            <link>https://example.org/old</link>
            <description>Autism research.</description>
            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
          </item>
          <item>
            <title>New astronomy discovery</title>
            <link>https://example.org/space</link>
            <description>Space science.</description>
            <pubDate>Sat, 14 Nov 2026 12:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""
        now = datetime(2026, 11, 15, tzinfo=timezone.utc)
        items = parse_feed(xml, "Teste", now)
        self.assertEqual(len(items), 1)
        self.assertIn("ADHD", items[0].title)
        self.assertGreater(items[0].score, 0)

    def test_parse_atom_feed(self):
        xml = """<feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Autistic young people and school inclusion</title>
            <link href="https://example.org/atom" />
            <summary>Research on autism and education.</summary>
            <updated>2026-11-14T09:00:00Z</updated>
          </entry>
        </feed>"""
        items = parse_feed(xml, "Atom", datetime(2026, 11, 15, tzinfo=timezone.utc))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://example.org/atom")

    def test_report_includes_human_review_warning(self):
        xml = """<rss><channel><item><title>Autism and learning</title>
        <link>https://example.org/a</link><description>Autism research.</description>
        <pubDate>Sat, 14 Nov 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
        items = parse_feed(xml, "Teste", datetime(2026, 11, 15, tzinfo=timezone.utc))
        report = build_report(items, [], datetime(2026, 11, 15, tzinfo=timezone.utc))
        self.assertIn("Uso interno", report)
        self.assertIn("Checklist de triagem humana", report)
        self.assertIn("https://example.org/a", report)


if __name__ == "__main__":
    unittest.main()
