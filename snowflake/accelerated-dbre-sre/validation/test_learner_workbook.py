#!/usr/bin/env python3
"""Offline-only learner workbook QA.

Checks question coverage, absence of solutions/answer-key links and V03/V04/V05
truthful boundaries. This does not assess a human learner or execute SQL.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "validation" / "LEARNER-OFFLINE-WORKBOOK.md"


def sections(text):
    heads = list(re.finditer(r"(?m)^## Level ([1-7]) — (.+)$", text))
    output = {}
    for index, head in enumerate(heads):
        last = heads[index+1].start() if index + 1 < len(heads) else text.index("## Final integrated tabletop")
        output[int(head.group(1))] = text[head.end():last]
    return output


class LearnerWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workbook = WORKBOOK.read_text(encoding="utf-8")
        cls.sections = sections(cls.workbook)

    def test_seven_levels_only(self):
        self.assertEqual(list(range(1, 8)), list(self.sections))

    def test_five_questions_per_level(self):
        for level, block in self.sections.items():
            matches = re.findall(r"(?m)^([1-5])\. (.+)$", block)
            self.assertEqual(5, len(matches), level)
            self.assertEqual(["1", "2", "3", "4", "5"], [x[0] for x in matches], level)
            for _, question in matches:
                self.assertGreaterEqual(len(question), 25, (level, question))

    def test_each_level_has_applied_exercise_and_safety_check(self):
        for level, block in self.sections.items():
            self.assertIn("### Applied offline exercise", block, level)
            self.assertIn("**Safety check:**", block, level)
            self.assertIn("**Reference:** [Level ", block, level)
            self.assertIn("[write here privately]", block, level)

    def test_seven_tabletop_cases(self):
        table = self.workbook.split("## Final integrated tabletop", 1)[1].split("## Learner completion checklist",1)[0]
        self.assertEqual(list("ABCDEFG"), re.findall(r"(?m)^\| ([A-G]) — ", table))

    def test_no_instructor_answers_leaked_to_learner_pack(self):
        # The learner edition should not expose instructor answer-key filenames or model results.
        for forbidden in ("INSTRUCTOR-ANSWER-KEY-RUBRICS.md",
                          "INSTRUCTOR-OFFLINE-ACCEPTANCE.md",
                          "INSTRUCTOR-SCORING-SHEET.md",
                          "EAST=2/170", "EAST 2/170", "WEST=1/80",
                          "54,110", "5,060",
                          "## Knowledge check (with answers)"):
            self.assertNotIn(forbidden, self.workbook)
        self.assertIn("not solutions", self.workbook)

    def test_strict_offline_and_privacy_boundaries(self):
        for marker in ("Do not execute SQL", "without a Snowflake account",
                       "All scenarios", "fictional", "approved private location",
                       "not actual Snowflake query evidence"):
            self.assertIn(marker.lower(), self.workbook.lower())

    def test_certification_status_precise(self):
        for marker in ("USER-DEFERRED / NOT RUN, 0/7",
                       "SKIPPED BY OWNER / NOT APPROVED",
                       "NOT CERTIFIED", "NOT ASSESSED"):
            self.assertIn(marker, self.workbook)

    def test_knowledge_and_tabletop_scores_not_combined(self):
        for marker in ("10 points per level", "14-point tabletop",
                       "Do not add the two scores"):
            self.assertIn(marker, self.workbook)

    def test_course_links_are_correct(self):
        for level, block in self.sections.items():
            m = re.search(r"\*\*Reference:\*\* \[Level (\d+) course\]\(([^)]+)\)", block)
            self.assertIsNotNone(m, level)
            self.assertEqual(str(level), m.group(1))
            resolved = (WORKBOOK.parent / m.group(2)).resolve()
            self.assertTrue(resolved.is_file(), (level, m.group(2)))

if __name__ == "__main__":
    unittest.main()
