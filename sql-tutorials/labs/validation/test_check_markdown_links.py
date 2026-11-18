#!/usr/bin/env python3
"""Offline regression tests for check_markdown_links.py.

Uses a temporary synthetic 120-chapter checkout. Does not access GitHub or a database.
Run: python -m unittest sql-tutorials/labs/validation/test_check_markdown_links.py -v
Requires markdown-it-py>=3,<5.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).with_name("check_markdown_links.py")


class MarkdownCheckerRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scope = self.root / "sql-tutorials"
        validation = self.scope / "labs" / "validation"
        validation.mkdir(parents=True)
        shutil.copyfile(CHECKER, validation / CHECKER.name)
        for name in ("MASTER-TOC.md", "README.md", "STATUS-TRACKER.md"):
            (self.scope / name).write_text("# " + name + "\n", encoding="utf-8")
        for n in range(1, 121):
            part = self.scope / f"part-{(n - 1) // 10 + 1:02d}-synthetic"
            part.mkdir(exist_ok=True)
            (part / f"{n:03d}-example.md").write_text(
                f"# Chapter {n:03d}\n\n[Home](../README.md)\n", encoding="utf-8"
            )

    def run_checker(self):
        script = self.scope / "labs" / "validation" / CHECKER.name
        output = self.root / "result.json"
        proc = subprocess.run(
            [sys.executable, str(script), "--json", str(output)],
            cwd=self.root, text=True, capture_output=True, check=False,
        )
        self.assertTrue(output.exists(), proc.stderr)
        return proc.returncode, json.loads(output.read_text(encoding="utf-8"))

    def test_complete_synthetic_checkout_passes(self):
        code, report = self.run_checker()
        self.assertEqual(code, 0, report["issues"])
        self.assertEqual(report["chapter_files"], 120)
        self.assertEqual(report["issues"], [])

    def test_missing_chapter_fails(self):
        (self.scope / "part-01-synthetic" / "001-example.md").unlink()
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x.get("chapter") == "001" and
                            x["issue"] == "missing chapter number"
                            for x in report["issues"]))

    def test_duplicate_chapter_fails(self):
        (self.scope / "part-01-synthetic" / "001-copy.md").write_text(
            "# Duplicate\n", encoding="utf-8"
        )
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "duplicate chapter number"
                            for x in report["issues"]))

    def test_broken_local_link_fails(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Missing](not-here.md)\n", encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "missing target"
                            for x in report["issues"]))

    def test_missing_fragment_fails(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Missing](../README.md#absent)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any("unmatched approximate GitHub heading slug" == x["issue"]
                            for x in report["issues"]))

    def test_outside_repository_link_fails(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Outside](../../../../outside.md)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "outside repository"
                            for x in report["issues"]))


if __name__ == "__main__":
    unittest.main()
