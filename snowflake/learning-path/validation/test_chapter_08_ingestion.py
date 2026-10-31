#!/usr/bin/env python3
"""Chapter 08 offline source and sample-data guardrails; no Snowflake access."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHAPTER = ROOT / "chapters" / "chapter-08-data-loading-and-ingestion.md"
EXERCISE = ROOT / "exercises" / "chapter-08-ingestion-tabletop.md"

class IngestionChapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chapter = CHAPTER.read_text(encoding="utf-8")
        cls.exercise = EXERCISE.read_text(encoding="utf-8")

    def test_chapter_has_all_seven_expected_sections(self):
        for section in ("## Learning objectives", "## 60-minute lesson plan",
                        "## Core concepts", "## Hands-on lab and expected results",
                        "## DBRE/SRE troubleshooting quick reference",
                        "## Knowledge check (with answers)",
                        "## Operational safety and validation",
                        "## Official documentation"):
            self.assertIn(section, self.chapter)

    def test_synthetic_csv_counts_and_sums(self):
        expected = [(101,"EAST","120"),(102,"WEST","80"),
                    (103,"EAST","50"),(104,"WEST","not_a_number")]
        for order,region,amount in expected:
            row=f"{order},{region},{amount}"
            self.assertIn(row, self.chapter)
            self.assertIn(row, self.exercise)
        parseable=[int(amount) for _,_,amount in expected if amount.isdigit()]
        self.assertEqual([120,80,50],parseable)
        self.assertEqual(250,sum(parseable))
        self.assertIn("not an observed successful load", self.chapter)

    def test_validation_mode_does_not_mutate_data(self):
        self.assertIn("VALIDATION_MODE = RETURN_ERRORS",self.chapter)
        self.assertIn("not supported for every", self.chapter)
        self.assertIn("without loading", self.chapter)
        self.assertNotIn("FORCE = TRUE;",self.chapter)
        self.assertNotIn("PURGE = TRUE",self.chapter)

    def test_load_history_and_replay_limits_are_explicit(self):
        for marker in ("INFORMATION_SCHEMA.COPY_HISTORY",
                       "SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY",
                       "14 days", "365 days",
                       "quarantin", "idempotency", "replay"):
            self.assertIn(marker.lower(),self.chapter.lower())

    def test_five_beginner_answers_and_separate_question_prompts(self):
        section=self.chapter.split("## Knowledge check (with answers)")[1].split("## Operational safety and validation")[0]
        self.assertEqual(5,len(re.findall(r"(?m)^[1-5]\. \*\*",section)))
        learner=self.exercise.split("## Five learner knowledge questions")[1].split("## Safety and final handoff")[0]
        self.assertEqual(5,len(re.findall(r"(?m)^[1-5]\. ",learner)))
        self.assertNotIn("## Knowledge check (with answers)", self.exercise)

    def test_evidence_and_approval_boundaries(self):
        for doc in (self.chapter,self.exercise):
            for marker in ("NOT RUN","NOT APPROVED","NOT CERTIFIED",
                           "V03","V04","V05"):
                self.assertIn(marker,doc)
            self.assertIn("offline",doc.lower())

    def test_no_real_sensitive_data_or_account_required(self):
        for marker in ("no Snowflake account", "fictional", "Do not execute"):
            self.assertIn(marker.lower(), self.chapter.lower())
        self.assertIn("No account",self.exercise)

    def test_linked_canonical_sources_are_present(self):
        for name in ("11-stages-internal-external.md",
                     "12-file-formats.md",
                     "13-copy-into-bulk-data-loading.md",
                     "15-data-loading-troubleshooting-validation.md",
                     "16-snowpipe.md"):
            self.assertIn(name,self.chapter)
            self.assertTrue((ROOT.parent / name).is_file())

if __name__ == "__main__":
    unittest.main()
