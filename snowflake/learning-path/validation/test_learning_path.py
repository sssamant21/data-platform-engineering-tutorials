#!/usr/bin/env python3
"""Ensure Snowflake learning-path navigation never duplicates tutorial content.

Local, offline source checks only. No Snowflake account, SQL or review actions.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SNOWFLAKE = ROOT.parent
INDEX = ROOT / "README.md"
STATUS = ROOT / "STATUS.md"
WORKSHEET = ROOT / "exercises" / "chapter-08-ingestion-tabletop.md"
LINK = re.compile(r"\]\(([^)]+)\)")

COURSES = (
    "level-01-snowflake-fundamentals.md",
    "level-02-administration-fundamentals.md",
    "level-03-performance-query-optimization.md",
    "level-04-monitoring-observability-cost.md",
    "level-05-security-rbac-governance.md",
    "level-06-data-recovery-disaster-recovery.md",
    "level-07-production-incident-response.md",
)
INGESTION = (
    "11-stages-internal-external.md",
    "12-file-formats.md",
    "13-copy-into-bulk-data-loading.md",
    "15-data-loading-troubleshooting-validation.md",
    "16-snowpipe.md",
)
CDC = (
    "18-streams-change-data-capture.md",
    "19-tasks-scheduled-processing.md",
    "21-streams-tasks-production-pipelines.md",
    "22-merge-upsert-incremental-processing.md",
)

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

class NavigationOnlyLearningPath(unittest.TestCase):
    def test_no_duplicate_markdown_chapters(self):
        copies = list((ROOT / "chapters").glob("*.md")) if (ROOT / "chapters").exists() else []
        self.assertEqual([], copies, "Remove copied tutorials; keep a link-only learning path")
        self.assertFalse((ROOT / "chapters" / "chapter-09-streams-tasks-incremental-pipelines.md").exists())

    def test_single_authoritative_accelerated_source(self):
        index = read(INDEX)
        for source in COURSES:
            self.assertTrue((SNOWFLAKE / "accelerated-dbre-sre" / source).is_file())
            self.assertIn(f"../accelerated-dbre-sre/{source}", index)
        self.assertIn("420 minutes", index)

    def test_canonical_ingestion_and_cdc_sources(self):
        index = read(INDEX)
        for source in (*INGESTION, *CDC):
            self.assertTrue((SNOWFLAKE / source).is_file(), source)
            self.assertIn(f"../{source}", index)

    def test_local_links_in_index_status_and_worksheet(self):
        checked = 0
        for path in (INDEX, STATUS, WORKSHEET):
            for href in LINK.findall(read(path)):
                target = href.split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                self.assertTrue((path.parent / target).resolve().is_file(),
                                f"{path.relative_to(ROOT)} -> {target}")
                checked += 1
        self.assertGreaterEqual(checked, 25)

    def test_index_no_copied_chapter_links_or_duplicate_claims(self):
        index = read(INDEX)
        self.assertNotIn("(chapters/", index)
        self.assertIn("no tutorial chapter copies", index)
        self.assertIn("navigation-only", index.lower())
        self.assertNotIn("480 minutes", index)
        self.assertIn("self-paced", index)

    def test_worksheet_retained_without_model_answers(self):
        data = read(WORKSHEET)
        self.assertIn("order_id,region,amount", data)
        self.assertIn("104,WEST,not_a_number", data)
        self.assertNotIn("../chapters/", data)
        self.assertIn("without model answers", data)
        self.assertIn("No SQL was run", data)

    def test_no_unearned_operational_acceptance(self):
        for path in (INDEX, STATUS, WORKSHEET):
            text = read(path).upper()
            for value in ("NOT RUN", "NOT APPROVED", "NOT CERTIFIED"):
                self.assertIn(value, text)

    def test_original_canonical_and_accelerated_tracks_unmodified_in_scope(self):
        self.assertTrue((SNOWFLAKE / "MASTER-LAYOUT.md").is_file())
        self.assertTrue((SNOWFLAKE / "accelerated-dbre-sre" / "README.md").is_file())
        self.assertIn("authoritative tutorial source", read(INDEX).lower())

if __name__ == "__main__":
    unittest.main()
