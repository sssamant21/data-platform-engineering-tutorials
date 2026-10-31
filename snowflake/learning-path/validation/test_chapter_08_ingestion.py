#!/usr/bin/env python3
"""Offline safety checks for unique Chapter 08 paper worksheet, not a duplicate lesson."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = ROOT / "exercises" / "chapter-08-ingestion-tabletop.md"

class IngestionExerciseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheet = EXERCISE.read_text(encoding="utf-8")

    def test_synthetic_csv_scenario(self):
        rows = [(101,"EAST","120"),(102,"WEST","80"),
                (103,"EAST","50"),(104,"WEST","not_a_number")]
        for row in rows:
            self.assertIn(",".join(map(str, row)), self.sheet)
        self.assertEqual(250, sum(int(v) for _,_,v in rows if v.isdigit()))

    def test_paper_exercises_and_question_count(self):
        for section in ("Part A — Architecture", "Part B — File validation",
                        "Part C — Safe ingestion triage", "Part D — Retry"):
            self.assertIn(section, self.sheet)
        part = self.sheet.split("## Five learner knowledge questions")[1]
        self.assertEqual(5, len(re.findall(r"(?m)^[1-5]\. ", part)))

    def test_references_single_existing_canonical_source(self):
        for name in ("11-stages-internal-external.md",
                     "12-file-formats.md",
                     "13-copy-into-bulk-data-loading.md",
                     "15-data-loading-troubleshooting-validation.md",
                     "16-snowpipe.md"):
            self.assertIn(name, self.sheet)
            self.assertTrue((ROOT.parent / name).is_file())

    def test_not_a_duplicate_tutorial_or_answer_key(self):
        self.assertNotIn("../chapters/", self.sheet)
        self.assertIn("without model answers", self.sheet)
        self.assertNotIn("## Knowledge check (with answers)", self.sheet)
        self.assertNotIn("## 60-minute lesson plan", self.sheet)

    def test_offline_privacy_and_noncertification(self):
        for term in ("No account", "No SQL was run", "NOT ASSESSED",
                     "NOT RUN", "NOT APPROVED", "NOT CERTIFIED",
                     "private learning location"):
            self.assertIn(term.lower(), self.sheet.lower())

if __name__ == "__main__":
    unittest.main()
