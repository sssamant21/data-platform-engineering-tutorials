#!/usr/bin/env python3
"""Source-only QA for beginner glossary and offline seven-session delivery plan.

Tests do not use Snowflake, authorize training, grade a learner or certify operations.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "validation"
GLOSSARY = VALIDATION / "BEGINNER-SNOWFLAKE-GLOSSARY.md"
CHECKLIST = VALIDATION / "COURSE-DELIVERY-CHECKLIST.md"

def level_sections(doc: str) -> dict[int, str]:
    markers = list(re.finditer(r"(?m)^## Level ([1-7]) — .+$", doc))
    return {
        int(match.group(1)): doc[match.end():(markers[i + 1].start() if i + 1 < len(markers) else len(doc))]
        for i, match in enumerate(markers)
    }


class GlossaryAndDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.glossary = GLOSSARY.read_text(encoding="utf-8")
        cls.checklist = CHECKLIST.read_text(encoding="utf-8")
        cls.glevels = level_sections(cls.glossary)
        cls.clevels = level_sections(cls.checklist)

    def test_both_documents_cover_exactly_seven_levels(self):
        self.assertEqual(list(range(1, 8)), list(self.glevels))
        self.assertEqual(list(range(1, 8)), list(self.clevels))

    def test_glossary_contains_beginner_terms_across_levels(self):
        total = 0
        for level, section in self.glevels.items():
            # Term table rows have three cells; headers and separator rows are excluded.
            terms = re.findall(r"(?m)^\| ([^|\n]+) \| (.+?) \| (.+?) \|$", section)
            terms = [(name, definition, caution) for name, definition, caution in terms
                     if name != "Term" and not name.startswith("---")]
            self.assertGreaterEqual(len(terms), 7, level)
            total += len(terms)
            for name, definition, caution in terms:
                self.assertGreaterEqual(len(name), 2)
                self.assertGreaterEqual(len(definition), 30, (level, name))
                self.assertGreaterEqual(len(caution), 10, (level, name))  # Short clarifying warnings are valid
        self.assertGreaterEqual(total, 60)

    def test_key_snowflake_concepts_are_present(self):
        for term in (
            "Database", "Schema", "Virtual warehouse", "Micro-partition",
            "Query Profile", "AVG_QUEUED_LOAD", "CREDITS_BILLED",
            "Resource monitor", "Masking policy", "Time Travel",
            "Fail-safe", "RPO", "RTO", "RCA",
        ):
            self.assertIn(term, self.glossary)

    def test_exact_same_five_agenda_blocks_and_60_minutes(self):
        total = 0
        for level in range(1, 8):
            section = self.clevels[level].split("**Deliverable:**", 1)[0]
            rows = re.findall(r"(?m)^\| [^|\n]+ \|\s*(\d+)\s*\|\s*\[ \] .+ \|$", section)
            self.assertEqual(5, len(rows), level)
            count = sum(map(int, rows))
            self.assertEqual(60, count, level)
            total += count
        self.assertEqual(420, total)

    def test_each_course_has_deliverable_and_safety_prompt(self):
        for level, section in self.clevels.items():
            self.assertIn("**Deliverable:**", section, level)
            self.assertIn("**Safety prompt:**", section, level)

    def test_delivery_uses_only_fictional_exercises(self):
        for value in ("OFFLINE / PAPER / TABLETOP ONLY", "no Snowflake account",
                      "do not execute", "fictional", "private"):
            self.assertIn(value.lower(), self.checklist.lower())
        self.assertIn("no Snowflake account", self.glossary)

    def test_training_certification_boundaries_not_overstated(self):
        for doc in (self.glossary, self.checklist):
            for phrase in ("V03", "NOT RUN", "V04", "NOT APPROVED", "V05", "NOT CERTIFIED"):
                self.assertIn(phrase, doc)

    def test_guide_separates_student_and_instructor_materials(self):
        self.assertIn("Keep the [instructor answer key]", self.checklist)
        self.assertIn("separate", self.checklist)
        self.assertIn("learner workbook", self.checklist)

    def test_markdown_links_resolve_for_both(self):
        for path, source in ((GLOSSARY, self.glossary), (CHECKLIST, self.checklist)):
            matches = list(re.finditer(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)", source))
            self.assertGreaterEqual(len(matches), 6)
            for match in matches:
                target = match.group(1).split("#", 1)[0]
                if target.startswith(("https://", "http://", "mailto:")):
                    continue
                self.assertTrue((path.parent / target).resolve().is_file(), (path, target))

    def test_no_fake_training_completion(self):
        for phrase in ("NOT ASSESSED", "no training has been delivered", "NOT CERTIFIED"):
            self.assertIn(phrase.lower(), self.checklist.lower())
        self.assertIn("No independent review", self.glossary)

if __name__ == "__main__":
    unittest.main()
