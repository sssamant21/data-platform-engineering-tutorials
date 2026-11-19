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


    def test_wrong_part_directory_fails(self):
        original = self.scope / "part-01-synthetic" / "001-example.md"
        wrong = self.scope / "part-02-synthetic" / "001-example.md"
        original.rename(wrong)
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "chapter number outside expected part"
                            for x in report["issues"]))

    def test_broken_link_in_nonchapter_markdown_fails(self):
        (self.scope / "README.md").write_text(
            "# Home\n[Broken](missing-guide.md)\n", encoding="utf-8"
        )
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "missing target" and
                            x["file"] == "sql-tutorials/README.md"
                            for x in report["issues"]))

    def test_duplicate_heading_fragment_suffix(self):
        (self.scope / "README.md").write_text(
            "# Home\n## Repeat\n## Repeat\n", encoding="utf-8"
        )
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Second](../README.md#repeat-1)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertEqual(code, 0, report["issues"])

    def test_multiline_setext_heading_fragment(self):
        (self.scope / "README.md").write_text(
            "Multi\nline\n==========\n", encoding="utf-8"
        )
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Heading](../README.md#multi-line)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertEqual(code, 0, report["issues"])


    def test_missing_local_image_fails(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n![Diagram](missing-diagram.png)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "missing target" and
                            x.get("href") == "missing-diagram.png"
                            for x in report["issues"]))

    def test_reference_style_link_missing_target_fails(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Guide][guide]\n\n[guide]: missing-guide.md\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "missing target" for x in report["issues"]))

    def test_broken_link_in_lab_guide_fails(self):
        guide = self.scope / "labs" / "validation" / "guide.md"
        guide.write_text("# Guide\n[Absent](missing-evidence.json)\n",
                         encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "missing target" and
                            x["file"].endswith("labs/validation/guide.md")
                            for x in report["issues"]))

    def test_malformed_url_reports_issue_without_crashing(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Bad](<https://[broken>)\n", encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "malformed URL" for x in report["issues"]))

    def test_valid_external_url_is_not_claimed_as_checked(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Reference](https://www.postgresql.org/docs/18/)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertEqual(code, 0, report["issues"])
        self.assertEqual(report["counts"].get("external_not_tested"), 1)


    def test_http_url_without_hostname_fails(self):
        p = self.scope / "part-01-synthetic" / "001-example.md"
        p.write_text("# Chapter 001\n[Bad](https:///missing-host)\n",
                     encoding="utf-8")
        code, report = self.run_checker()
        self.assertNotEqual(code, 0)
        self.assertTrue(any(x["issue"] == "malformed URL"
                            for x in report["issues"]))
        self.assertEqual(report["counts"].get("external_not_tested", 0), 0)


if __name__ == "__main__":
    unittest.main()
