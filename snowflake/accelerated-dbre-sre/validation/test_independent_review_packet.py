#!/usr/bin/env python3
"""Source-only checks for the independent-review handoff.

No human review is performed here; a PASS cannot be a reviewer approval.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "validation" / "V04-INDEPENDENT-REVIEW-PACKET.md"


class ReviewerHandoffContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PACKET.read_text(encoding="utf-8")

    def test_five_distinct_review_areas(self):
        for role in ("R1 — Instructor/novice learner", "R2 — Snowflake DBRE/administrator",
                     "R3 — Security/IAM and data owner", "R4 — Application/FinOps",
                     "R5 — DR/incident operations"):
            self.assertIn(role, self.text)

    def test_no_pretend_approvals_or_github_reviewers(self):
        for label in ("AWAITING REVIEWER ASSIGNMENT", "NO INDEPENDENT REVIEWS",
                      "NOT_ASSIGNED", "NOT PROVIDED", "NOT_REVIEWED",
                      "No reviewers were invented or auto-assigned"):
            self.assertIn(label, self.text)

    def test_runtime_and_production_borders(self):
        for label in ("USER-DEFERRED / NOT RUN", "BLOCKED: V03 0/7",
                      "V04 is PENDING", "V05 is NOT CERTIFIED",
                      "DRAFT / NOT AUTHORIZED"):
            self.assertIn(label, self.text)

    def test_reviewers_have_actionable_checklists_and_findings_schema(self):
        for title in ("### R1 —", "### R2 —", "### R3 —", "### R4 —",
                      "### R5 —", "## Defect and follow-up register",
                      "## Review handoff evidence"):
            self.assertIn(title, self.text)
        for marker in ("P0/P1", "Reviewer/review URL", "File/line",
                       "Fix commit / retest", "Commit SHA reviewed"):
            self.assertIn(marker, self.text)

    def test_cross_referenced_release_docs_are_local(self):
        for fname in ("OFFLINE-RELEASE-INVENTORY.md", "V04-V05-REVIEWER-HANDOFF.md",
                      "VALIDATION-PLAN.md", "V03-PREFLIGHT-STATUS.md"):
            self.assertIn(fname, self.text)
            self.assertTrue((PACKET.parent / fname).is_file())

    def test_currrent_status_and_pr_remain_unapproved(self):
        status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("V04 formal independent acceptance", status)
        self.assertIn("**PENDING**", status)
        self.assertIn("**NOT CERTIFIED**", status)
        self.assertIn("**DEFERRED — 0/7 RUN**", status)


if __name__ == "__main__":
    unittest.main()
