#!/usr/bin/env python3
"""Offline positive/negative checks for the Chapters 01–04 documentation contract."""
import pathlib
import tempfile
import unittest

from ch01_04_contract import CHAPTERS, check


class ChapterContractTests(unittest.TestCase):
    def make_chapters(self, root):
        for n, (filename, terms) in CHAPTERS.items():
            headings = "\n".join("## " + term.title() for term in terms)
            (root / filename).write_text(
                "# Synthetic Chapter\n"
                "**Status:** Runtime lab validation pending\n"
                + headings + "\n```javascript\nprint('synthetic')\n```\n",
                encoding="utf-8",
            )

    def test_valid_synthetic_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_chapters(root)
            result = check(root)
            self.assertTrue(result["passed"], result)
            self.assertFalse(result["runtime_certified"])

    def test_missing_chapter_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_chapters(root)
            (root / CHAPTERS[3][0]).unlink()
            result = check(root)
            self.assertFalse(result["passed"])
            self.assertIn("missing chapter", result["results"][2]["errors"])

    def test_missing_failure_contract_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_chapters(root)
            file = root / CHAPTERS[1][0]
            file.write_text(file.read_text().replace("## Failure", "## Not a negative test"))
            result = check(root)
            self.assertFalse(result["passed"])
            self.assertIn("missing heading contract: failure", result["results"][0]["errors"])

    def test_runtime_pending_disclaimer_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            self.make_chapters(root)
            file = root / CHAPTERS[4][0]
            file.write_text(file.read_text().replace("Runtime lab validation pending", "Completed"))
            result = check(root)
            self.assertFalse(result["passed"])
            self.assertTrue(any("disclaimer" in error for error in result["results"][3]["errors"]))


if __name__ == "__main__":
    unittest.main()
