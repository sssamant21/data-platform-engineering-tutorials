#!/usr/bin/env python3
"""Offline checks for the independent Snowflake Learning Path chapter layout.

No Snowflake connection, SQL execution, credential use or reviewer acceptance.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNOWFLAKE = ROOT.parent
ORIGINAL = SNOWFLAKE / "accelerated-dbre-sre"
CHAPTERS = (
    ("chapter-01-snowflake-fundamentals.md", "level-01-snowflake-fundamentals.md"),
    ("chapter-02-snowflake-administration.md", "level-02-administration-fundamentals.md"),
    ("chapter-03-performance-query-optimization.md", "level-03-performance-query-optimization.md"),
    ("chapter-04-monitoring-observability-cost.md", "level-04-monitoring-observability-cost.md"),
    ("chapter-05-security-rbac-governance.md", "level-05-security-rbac-governance.md"),
    ("chapter-06-data-recovery-disaster-recovery.md", "level-06-data-recovery-disaster-recovery.md"),
    ("chapter-07-troubleshooting-incident-response.md", "level-07-production-incident-response.md"),
)
MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")
AGENDA = re.compile(r"^\|[^|\n]+\|\s*(\d+)\s+min\s*\|", re.MULTILINE)
CODE = re.compile(r"(?ms)^~~~sql\s*\n(.*?)^~~~\s*$")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SnowflakeLearningPathTests(unittest.TestCase):
    def test_exactly_seven_numbered_chapters(self):
        found = sorted(p.name for p in (ROOT / "chapters").glob("chapter-*.md"))
        self.assertEqual(sorted(name for name, _ in CHAPTERS), found)

    def test_chapter_titles_and_sixty_minute_agendas(self):
        total = 0
        for i, (name, _) in enumerate(CHAPTERS, 1):
            text = read(ROOT / "chapters" / name)
            self.assertTrue(text.startswith(f"# Chapter {i:02d} — "), name)
            self.assertIn("**60 min**", text)
            agenda = text.split("## 60-minute lesson plan", 1)[1].split("## Core concepts", 1)[0]
            minutes = list(map(int, AGENDA.findall(agenda)))
            self.assertEqual(5, len(minutes), name)
            self.assertEqual(60, sum(minutes), name)
            total += sum(minutes)
        self.assertEqual(420, total)

    def test_each_chapter_preserves_full_teaching_sections(self):
        for name, original in CHAPTERS:
            text = read(ROOT / "chapters" / name)
            old = read(ORIGINAL / original)
            for section in ("## Learning objectives", "## Core concepts",
                            "## Hands-on lab and expected results",
                            "## DBRE/SRE troubleshooting quick reference",
                            "## Knowledge check (with answers)",
                            "## Operational safety and validation",
                            "## Official documentation"):
                self.assertIn(section, text, (name, section))
            self.assertEqual(len(CODE.findall(old)), len(CODE.findall(text)), name)
            self.assertGreater(len(CODE.findall(text)), 0, name)

    def test_copied_core_sections_match_original_lessons(self):
        # Ignore the changed locations of Markdown links but require teaching text parity.
        for name, original in CHAPTERS:
            current = read(ROOT / "chapters" / name)
            prior = read(ORIGINAL / original)
            def extract(source):
                area = source.split("## Core concepts", 1)[1]
                area = area.split("## Continue into the full 90-chapter curriculum", 1)[0]
                return MARKDOWN_LINK.sub("](__LINK__)", area).strip()
            self.assertEqual(extract(prior), extract(current), name)

    def test_all_relative_chapter_and_index_links_exist(self):
        docs = [ROOT / "README.md", ROOT / "STATUS.md",
                *(ROOT / "chapters" / name for name, _ in CHAPTERS)]
        checked = 0
        for path in docs:
            for link in MARKDOWN_LINK.findall(read(path)):
                target = link.split("#", 1)[0]
                if not target or target.startswith(("https://", "http://", "mailto:")):
                    continue
                self.assertTrue((path.parent / target).resolve().is_file(),
                                f"{path.relative_to(ROOT)} -> {target}")
                checked += 1
        self.assertGreaterEqual(checked, 80)

    def test_index_and_status_have_seven_correct_links(self):
        for name, _ in CHAPTERS:
            for index in ("README.md", "STATUS.md"):
                self.assertIn(f"chapters/{name}", read(ROOT / index))

    def test_no_fake_runtime_review_or_certification(self):
        for name, _ in CHAPTERS:
            text = read(ROOT / "chapters" / name)
            self.assertIn("Snowflake runtime validation NOT RUN (deferred)", text)
            self.assertIn("independent review SKIPPED BY OWNER / NOT APPROVED", text)
        for index in ("README.md", "STATUS.md"):
            text = read(ROOT / index)
            for marker in ("NOT RUN", "NOT APPROVED", "NOT CERTIFIED", "draft"):
                self.assertIn(marker.lower(), text.lower())

    def test_index_links_to_original_accelerated_track_and_90_chapters(self):
        content = read(ROOT / "README.md")
        self.assertIn("../accelerated-dbre-sre/README.md", content)
        self.assertIn("../MASTER-LAYOUT.md", content)
        self.assertIn("seven accelerated tutorials", content)
        self.assertIn("420 minutes", content)


if __name__ == "__main__":
    unittest.main()
