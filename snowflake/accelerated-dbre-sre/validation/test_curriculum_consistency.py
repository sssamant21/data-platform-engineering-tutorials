#!/usr/bin/env python3
"""Offline cross-checks between accelerated lessons and manual Snowflake smoke SQL.

These guard selected semantic contracts only. No account connection, SQL parser,
runtime evidence, independent review, or certification is implied.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "validation" / "runtime"


def lesson(number: int) -> str:
    files = list(ROOT.glob(f"level-{number:02d}-*.md"))
    if len(files) != 1:
        raise AssertionError(f"Expected exactly one lesson for level {number}")
    return files[0].read_text(encoding="utf-8")


def smoke(number: int) -> str:
    file = RUNTIME / f"level-{number:02d}-smoke.sql"
    return file.read_text(encoding="utf-8")


def sql_blocks(source: str) -> str:
    return "\n".join(re.findall(r"(?ms)^~~~sql\s*\n(.*?)^~~~\s*$", source))


class CurriculumParityTests(unittest.TestCase):
    def test_seven_60_minute_lessons_retained(self):
        index = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("420 min", index)
        for n in range(1, 8):
            self.assertIn("**60 min**", lesson(n))

    def test_l1_same_synthetic_values_and_output_criteria(self):
        l1 = lesson(1)
        s1 = smoke(1)
        for fragment in ("'EAST',120", "'WEST',80", "'EAST',50"):
            self.assertIn(fragment, l1)
        for fragment in ("'EAST', 120", "'WEST', 80", "'EAST', 50"):
            self.assertIn(fragment, s1)
        self.assertIn("sales 170", l1)
        self.assertIn("sales 80", l1)
        self.assertIn("SUM(IFF(REGION = 'EAST', AMOUNT, 0)) = 170", s1)
        self.assertIn("SUM(IFF(REGION = 'WEST', AMOUNT, 0)) = 80", s1)
        # Different table identifiers are intentional for course vs dedicated QA smoke.
        self.assertIn("DBRE_SRE_L1_ORDERS", l1)
        self.assertIn("DBRE_SRE_L1_QA_20261030", s1)

    def test_l2_query_tag_matches_manual_smoke(self):
        l2 = sql_blocks(lesson(2))
        s2 = smoke(2)
        pattern = r"QUERY_TAG\s*=\s*'([A-Za-z0-9_]+)'"
        ltag = re.search(pattern, l2)
        stag = re.search(pattern, s2)
        self.assertIsNotNone(ltag)
        self.assertIsNotNone(stag)
        self.assertEqual(ltag.group(1), stag.group(1))
        self.assertIn("QUERY_HISTORY_BY_SESSION", l2)
        self.assertIn("QUERY_HISTORY_BY_SESSION", s2)
        self.assertIn("ALTER SESSION UNSET QUERY_TAG", l2)
        self.assertIn("ALTER SESSION UNSET QUERY_TAG", s2)

    def test_l3_same_session_scope_and_arithmetic(self):
        l3 = lesson(3)
        l3sql = sql_blocks(l3)
        s3 = smoke(3)
        self.assertIn("QUERY_HISTORY_BY_SESSION", l3sql)
        self.assertNotIn("QUERY_HISTORY_BY_USER", l3sql)
        self.assertIn("QUERY_HISTORY_BY_SESSION", s3)
        for expression in ("MOD(ORDER_ID, 10)", "MOD(ORDER_ID, 90)", "ROWCOUNT => 1000"):
            self.assertIn(expression, l3sql)
            self.assertIn(expression, s3)
        values = range(1, 1001)
        self.assertEqual(sum(10 + i % 90 for i in values), 54110)
        self.assertEqual(sum(10 + i % 90 for i in values if i % 10 == 1), 5060)
        for expected in ("54,110", "5,060"):
            self.assertIn(expected, l3)
        for expected in ("54110", "5060"):
            self.assertIn(expected, s3)
        self.assertIn("not a representative performance benchmark", l3)

    def test_l4_warehouse_metrics_and_billability(self):
        l4 = lesson(4)
        s4 = smoke(4)
        for view in (
            "WAREHOUSE_METERING_HISTORY", "WAREHOUSE_LOAD_HISTORY",
            "ACCOUNT_USAGE.QUERY_HISTORY", "METERING_DAILY_HISTORY",
        ):
            self.assertIn(view, l4)
            self.assertIn(view, s4)
        self.assertIn("CREDITS_BILLED", s4)
        self.assertIn("AVG_QUEUED_LOAD", s4)
        self.assertIn("EXECUTION_STATUS = 'fail'", s4)
        self.assertIn("not the account's final billed total", l4)

    def test_l5_audit_and_role_handoff_are_nondestructive(self):
        l5 = lesson(5)
        s5 = smoke(5)
        for snippet in ("CURRENT_SECONDARY_ROLES()", "SHOW GRANTS;", "SHOW ROLES;"):
            self.assertIn(snippet, l5)
            self.assertIn(snippet, s5)
        self.assertIn("ACCOUNT_USAGE.LOGIN_HISTORY", s5)
        self.assertNotIn("USER_NAME,", s5.split("SELECT DATE_TRUNC")[1])
        self.assertNotIn("CLIENT_IP,", s5.split("SELECT DATE_TRUNC")[1])

    def test_l6_retention_qualified_and_optional_nonprod(self):
        l6 = lesson(6)
        s6 = smoke(6)
        for term in ("MIN_DATA_RETENTION_TIME_IN_DAYS", "DATA_RETENTION_TIME_IN_DAYS"):
            self.assertIn(term, l6)
            self.assertIn(term, s6)
        self.assertNotIn("effective retention parameter rows", l6)
        self.assertIn("AT(OFFSET => -60)", l6)
        self.assertIn("AT (OFFSET => -60)", s6)
        self.assertIn("two rows", l6.lower())
        self.assertIn("do not substitute any production object", l6)

    def test_l7_recent_vs_historical_scopes(self):
        l7 = lesson(7)
        s7 = smoke(7)
        for term in ("QUERY_HISTORY_BY_SESSION", "ACCOUNT_USAGE.QUERY_HISTORY",
                     "QUEUED_OVERLOAD_TIME"):
            self.assertIn(term, l7)
            self.assertIn(term, s7)
        self.assertIn("`fail`", l7)
        self.assertIn("EXECUTION_STATUS = 'fail'", s7)
        self.assertIn("NOT RUN", l7)

    def test_no_runtime_acceptance_in_offline_curriculum(self):
        status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
        pack = (ROOT / "validation" / "INSTRUCTOR-OFFLINE-ACCEPTANCE.md").read_text(encoding="utf-8")
        handoff = (ROOT / "validation" / "V04-V05-REVIEWER-HANDOFF.md").read_text(encoding="utf-8")
        for n in range(1, 8):
            self.assertIn("Snowflake runtime validation NOT RUN (deferred)", lesson(n))
        self.assertIn("DEFERRED — 0/7 RUN", status)
        self.assertIn("NO live Snowflake labs have been executed", pack)
        self.assertIn("NO INDEPENDENT SIGN-OFF", handoff)
        self.assertIn("NOT CERTIFIED", handoff)


if __name__ == "__main__":
    unittest.main()
