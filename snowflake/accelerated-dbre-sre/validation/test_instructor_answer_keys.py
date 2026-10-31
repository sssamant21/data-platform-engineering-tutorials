#!/usr/bin/env python3
"""Offline quality gate for 35 annotated instructor answers and 7 tabletop rubrics.

This is a static Markdown and content-contract test; no Snowflake is queried.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

TRACK = Path(__file__).resolve().parents[1]
KEY = TRACK / "validation" / "INSTRUCTOR-ANSWER-KEY-RUBRICS.md"
PACK = TRACK / "validation" / "INSTRUCTOR-OFFLINE-ACCEPTANCE.md"


def source(level: int) -> str:
    files = list(TRACK.glob(f"level-{level:02d}-*.md"))
    if len(files) != 1:
        raise AssertionError(f"Expected one level {level:02d} lesson")
    return files[0].read_text(encoding="utf-8")


def knowledge_block(lesson: str) -> str:
    begin = lesson.index("## Knowledge check (with answers)")
    end = lesson.index("\n## ", begin + 5)
    return lesson[begin:end]


class InstructorAnswerKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = KEY.read_text(encoding="utf-8")
        cls.pack = PACK.read_text(encoding="utf-8")

    def test_exactly_five_explained_answers_per_level(self):
        for level in range(1, 8):
            block = knowledge_block(source(level))
            questions = re.findall(r"(?m)^([1-5])\. \*\*(.+?)\*\* (.+)$", block)
            self.assertEqual(5, len(questions), level)
            self.assertEqual(["1", "2", "3", "4", "5"], [n for n, _, _ in questions])
            for _, question, answer in questions:
                self.assertTrue(question.strip(), level)  # Short beginner questions are valid
                self.assertGreaterEqual(len(answer), 100, (level, question))
            self.assertIn("Instructor grading (offline)", block)
            self.assertIn("10 points", block)
            self.assertIn("not V03 runtime acceptance", block)

    def test_instructor_key_lists_all_five_questions_per_level(self):
        for level in range(1, 8):
            match = re.search(
                rf"(?ms)^## Level {level} — .*?\n(.*?)(?=^## Level |^## Detailed grading|\Z)",
                self.key,
            )
            self.assertIsNotNone(match, level)
            body = match.group(1)
            for n in range(1, 6):
                self.assertRegex(body, rf"(?m)^\| {n}\. ")
            self.assertEqual(5, len(re.findall(r"(?m)^\| [1-5]\. ", body)), level)

    def test_both_scoring_dimensions_are_separate(self):
        for marker in ("10 maximum", "14 maximum", "8/10", "12/14",
                       "two distinct scores", "critical safety"):
            self.assertIn(marker.lower(), self.key.lower())
        self.assertIn("12/14", self.pack)

    def test_all_seven_tabletop_cases_have_scoring_anchors(self):
        for case in ("A —", "B —", "C —", "D —", "E —", "F —", "G —"):
            self.assertIn(case, self.key)
            self.assertIn(case, self.pack)
        self.assertEqual(7, len(re.findall(r"(?m)^\| [A-G] — ", self.key)))

    def test_safety_critical_conditions_are_explicit(self):
        for marker in ("ACCOUNTADMIN", "patient data", "credentials",
                       "unapproved", "REMEDIATION_REQUIRED",
                       "independent review", "NOT CERTIFIED"):
            self.assertIn(marker.lower(), self.key.lower())

    def test_l1_l3_arithmetic_in_answer_keys(self):
        self.assertIn("EAST", source(1))
        self.assertIn("WEST", source(1))
        self.assertIn("170", source(1))
        self.assertIn("80", source(1))
        self.assertIn("54,110", source(3))
        self.assertIn("5,060", source(3))
        for term in ("EAST 2 / 170", "WEST 1 / 80", "1,000-row"):
            self.assertIn(term, self.key)

    def test_l4_grading_distinguishes_load_billing_and_serverless(self):
        key = self.key
        lesson = source(4)
        for fragment in ("AVG_QUEUED_LOAD", "resource monitors", "serverless", "budgets"):
            self.assertIn(fragment.lower(), key.lower())
            self.assertIn(fragment.lower() if fragment == "serverless" else fragment, lesson)

    def test_l5_l6_l7_have_precise_safety_boundaries(self):
        for level, expected in [
            (5, ("masking", "row access", "synthetic", "approval")),
            (6, ("RPO", "RTO", "Fail-safe", "retention")),
            (7, ("QUERY_ID", "overload", "blameless", "approval")),
        ]:
            body = knowledge_block(source(level)).lower()
            for phrase in expected:
                self.assertIn(phrase.lower(), body)

    def test_deferred_runtime_and_external_review_are_not_mislabeled(self):
        for term in ("V03", "V04", "V05", "NOT CERTIFIED",
                     "No Snowflake runtime tests were executed"):
            self.assertIn(term.lower(), self.key.lower())
        for level in range(1, 8):
            self.assertIn("Snowflake runtime validation NOT RUN (deferred)", source(level))


if __name__ == "__main__":
    unittest.main()
