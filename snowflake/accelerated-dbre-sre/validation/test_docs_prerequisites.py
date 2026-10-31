#!/usr/bin/env python3
"""Offline curriculum doc and prerequisite contracts, without Snowflake access.

This source test verifies selected local links and authored Markdown conventions.
It does NOT fetch external URLs, parse Snowflake SQL or certify any live lab.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSONS = sorted(ROOT.glob("level-0[1-7]-*.md"))
MD_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)")


def lesson(level: int) -> str:
    matched = [p for p in LESSONS if p.name.startswith(f"level-{level:02d}-")]
    if len(matched) != 1:
        raise AssertionError(f"Expected exactly one Level {level} Markdown lesson")
    return matched[0].read_text(encoding="utf-8")


class OfflineDocsPrerequisiteTests(unittest.TestCase):
    def test_seven_lessons_and_420_minutes(self):
        self.assertEqual(7, len(LESSONS))
        self.assertIn("420 min", (ROOT / "README.md").read_text(encoding="utf-8"))
        for level in range(1, 8):
            self.assertIn("**60 min**", lesson(level))

    def test_offline_learning_requires_no_account(self):
        for level in range(1, 8):
            content = lesson(level)
            self.assertIn("**Offline prerequisites:**", content)
            self.assertIn("no Snowflake account, CLI, credentials or live database access is required", content)
            self.assertIn("**Do not execute SQL for the offline course.**", content)
            self.assertNotIn("**Prerequisites:** Authorized Snowflake training account", content)

    def test_live_requirements_are_per_level_and_deferred(self):
        for level in range(1, 8):
            content = lesson(level)
            self.assertIn("**Deferred V03 live-lab prerequisites:**", content)
            self.assertIn("Approved nonproduction account", content)
            self.assertIn("Snowflake runtime validation NOT RUN (deferred)", content)

    def test_live_level_specific_safety_requirements(self):
        required = {
            1: ("scratch schema", "TEMP"),
            2: ("least-privilege", "INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION"),
            3: ("scratch schema", "Query Profile"),
            4: ("monitoring role", "SNOWFLAKE.ACCOUNT_USAGE"),
            5: ("security-owner", "LOGIN_HISTORY"),
            6: ("writable exercise", "scratch"),
            7: ("current-session query-history", "account-wide history"),
        }
        for level, clauses in required.items():
            live = lesson(level).split("**Deferred V03 live-lab prerequisites:**", 1)[1].split("\n\n", 1)[0]
            for clause in clauses:
                self.assertIn(clause, live, (level, clause))

    def test_current_documentation_url_and_canonical_query_profile(self):
        current = "https://docs.snowflake.com/en/user-guide/ui-snowsight-activity"
        deprecated = "https://docs.snowflake.com/en/user-guide/ui-query-profile"
        for level in range(1, 8):
            content = lesson(level)
            self.assertIn("## Official documentation", content)
            docs = content.split("## Official documentation", 1)[1]
            links = re.findall(r"https?://[^\s)]+", docs)
            self.assertTrue(links, level)
            for link in links:
                self.assertTrue(link.startswith("https://docs.snowflake.com/en/"), (level, link))
                self.assertNotIn(deprecated, link)
        for level in (3, 7):
            self.assertIn(current, lesson(level))

    def test_all_internal_links_in_release_package_resolve(self):
        docs = list(LESSONS) + [
            ROOT / "README.md",
            ROOT / "validation" / "INSTRUCTOR-OFFLINE-ACCEPTANCE.md",
            ROOT / "validation" / "INSTRUCTOR-ANSWER-KEY-RUBRICS.md",
            ROOT / "validation" / "OFFLINE-RELEASE-INVENTORY.md",
            ROOT / "validation" / "V02-DOCS-PREREQUISITES-REVIEW.md",
        ]
        checked = 0
        for path in docs:
            raw = path.read_text(encoding="utf-8")
            for match in MD_LINK.finditer(raw):
                target = match.group(1).split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                link = (path.parent / target).resolve()
                self.assertTrue(link.is_file(), f"{path.name} -> {target}")
                checked += 1
        self.assertGreaterEqual(checked, 50)

    def test_readme_separates_instructional_from_live_results(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for term in ("Offline mode (default", "no account or CLI",
                     "without executing it", "hypothetical, hand-computed",
                     "Deferred live-lab mode", "independent reviewers",
                     "final offline release-package inventory"):
            self.assertIn(term, readme)
        self.assertIn("No Snowflake account", readme)

    def test_final_inventory_covers_all_levels_and_gate_boundaries(self):
        inventory = (ROOT / "validation" / "OFFLINE-RELEASE-INVENTORY.md").read_text(encoding="utf-8")
        for level in range(1, 8):
            self.assertIn(f"| L{level} |", inventory)
        for term in ("INSTRUCTOR-ANSWER-KEY-RUBRICS.md", "INSTRUCTOR-SCORING-SHEET.md",
                     "test_docs_prerequisites.py", "V02-DOCS-PREREQUISITES-REVIEW.md",
                     "USER-DEFERRED / NOT RUN", "NOT CERTIFIED", "PENDING"):
            self.assertIn(term, inventory)

    def test_no_external_or_runtime_acceptance_is_claimed(self):
        audit = (ROOT / "validation" / "V02-DOCS-PREREQUISITES-REVIEW.md").read_text(encoding="utf-8")
        for required in ("spot-check", "not", "No live Snowflake queries",
                         "V03", "V04", "V05", "NOT CERTIFIED", "DRAFT"):
            self.assertIn(required.lower(), audit.lower())
        self.assertIn("No live Snowflake", (ROOT / "validation" / "OFFLINE-RELEASE-INVENTORY.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
