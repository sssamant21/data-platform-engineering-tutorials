"""Isolated unit tests for Redis Enterprise V01 structural checks."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_tutorials import audit


class V01AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "redis-enterprise"
        self.root.mkdir()
        for n in range(1, 81):
            (self.root / f"{n:02d}-chapter.md").write_text(
                f"# Chapter {n:02d} — Example\n\n```python\nprint('ok')\n```\n",
                encoding="utf-8")

    def check(self, **kw):
        return audit(self.root, minimum_bytes=0, **kw)

    def test_valid_eighty_chapters(self):
        result = self.check()
        self.assertEqual(result["summary"]["chapters_found"], 80)
        self.assertEqual(result["summary"]["python_blocks"], 80)
        self.assertEqual(result["summary"]["errors"], 0)

    def test_missing_chapter(self):
        (self.root / "20-chapter.md").unlink()
        result = self.check()
        self.assertIn("missing_chapter", [f["check"] for f in result["findings"]])

    def test_wrong_heading(self):
        (self.root / "04-chapter.md").write_text("# Chapter 99 — Incorrect\n", encoding="utf-8")
        self.assertIn("chapter_title", [f["check"] for f in self.check()["findings"]])

    def test_unclosed_code_fence(self):
        (self.root / "11-chapter.md").write_text("# Chapter 11\n```python\nprint('oops')\n", encoding="utf-8")
        self.assertIn("unclosed_fence", [f["check"] for f in self.check()["findings"]])

    def test_missing_local_link(self):
        (self.root / "05-chapter.md").write_text(
            "# Chapter 05\n[broken](missing.md)\n", encoding="utf-8")
        self.assertIn("broken_relative_link", [f["check"] for f in self.check()["findings"]])

    def test_valid_local_link(self):
        (self.root / "05-chapter.md").write_text(
            "# Chapter 05\n[good](06-chapter.md)\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result["summary"]["relative_links_checked"], 1)
        self.assertEqual(result["summary"]["errors"], 0)

    def test_python_syntax_warning_and_strict_option(self):
        (self.root / "05-chapter.md").write_text(
            "# Chapter 05\n```python\nif :\n```\n", encoding="utf-8")
        soft = self.check()
        hard = self.check(strict_python=True)
        self.assertEqual(soft["summary"]["python_syntax_errors"], 1)
        self.assertEqual(soft["summary"]["errors"], 0)
        self.assertGreater(hard["summary"]["errors"], 0)

    def test_links_inside_code_are_not_links(self):
        (self.root / "05-chapter.md").write_text(
            "# Chapter 05\n```text\n[fake](missing.md)\n```\n", encoding="utf-8")
        self.assertEqual(self.check()["summary"]["relative_links_checked"], 0)


if __name__ == "__main__":
    unittest.main()
