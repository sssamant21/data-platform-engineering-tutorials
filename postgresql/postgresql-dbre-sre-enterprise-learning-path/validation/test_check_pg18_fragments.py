#!/usr/bin/env python3
"""Offline unit tests for the PostgreSQL 18 fragment checker; no network calls.

Run: python -m unittest discover -s validation -p 'test_check_pg18_fragments.py' -v
(from the independent learning-path root).
"""
import io
import unittest
from unittest.mock import patch
from urllib.error import URLError

import check_pg18_fragments as checker


class FakeResponse:
    def __init__(self, body, url, content_type="text/html", status=200):
        self.body = io.BytesIO(body)
        self.url = url
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.body.close()

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.body.read(limit)


class FragmentCheckerTests(unittest.TestCase):
    URL = checker.TARGETS[2]
    PAGE = URL.split("#")[0]

    def inspect_with(self, html, final_url=None, content_type="text/html", status=200):
        response = FakeResponse(html.encode(), final_url or self.PAGE, content_type, status)
        with patch.object(checker, "urlopen", return_value=response):
            return checker.inspect(self.URL)

    def test_exact_id_present(self):
        result = self.inspect_with('<section id="FUNCTIONS-ADMIN-DBSIZE">ok</section>')
        self.assertEqual(result["status"], "anchor_present")

    def test_named_anchor_present(self):
        result = self.inspect_with('<a name="FUNCTIONS-ADMIN-DBSIZE"></a>')
        self.assertEqual(result["status"], "anchor_present")

    def test_section_text_is_not_anchor_proof(self):
        result = self.inspect_with("<h2>FUNCTIONS-ADMIN-DBSIZE</h2>")
        self.assertEqual(result["status"], "anchor_missing")

    def test_wrong_version_redirect_rejected(self):
        result = self.inspect_with("<p>ok</p>", "https://www.postgresql.org/docs/17/functions-admin.html")
        self.assertEqual(result["status"], "unexpected_redirect")

    def test_same_version_different_page_redirect_rejected(self):
        result = self.inspect_with("<p>ok</p>", "https://www.postgresql.org/docs/18/index.html")
        self.assertEqual(result["status"], "unexpected_redirect")

    def test_unexpected_host_rejected(self):
        result = self.inspect_with("<p>ok</p>", "https://example.org/docs/18/functions-admin.html")
        self.assertEqual(result["status"], "unexpected_redirect")

    def test_non_html_rejected(self):
        result = self.inspect_with("{}", content_type="application/json")
        self.assertEqual(result["status"], "unexpected_content_type")

    def test_oversize_rejected(self):
        result = self.inspect_with("x" * 5_000_001)
        self.assertEqual(result["status"], "oversize_response")

    def test_dns_failure_is_unverified(self):
        with patch.object(checker, "urlopen", side_effect=URLError("DNS unavailable")):
            result = checker.inspect(self.URL)
        self.assertEqual(result["status"], "unverified")
        self.assertIn("URLError", result["error"])


if __name__ == "__main__":
    unittest.main()
