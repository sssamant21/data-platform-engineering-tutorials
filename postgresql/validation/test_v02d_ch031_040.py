#!/usr/bin/env python3
"""V02-D Chapter 031-040 static operation contracts.

Do not execute SQL or modify a database. A contract pass is not PG18 runtime proof.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SQL = ROOT / "labs" / "sql"
IDS = [f"{i:03}" for i in range(31, 41)]


class Chapters031040Contracts(unittest.TestCase):
    def test_all_ten_chapters_have_matching_labs(self):
        for ident in IDS:
            chapters = list((ROOT / "chapters").glob(ident + "-*.md"))
            labs = list((ROOT / "labs").glob(ident + "-*-lab.md"))
            with self.subTest(chapter=ident):
                self.assertEqual(len(chapters), 1)
                self.assertEqual(len(labs), 1)
                self.assertIn("../labs/" + labs[0].name, chapters[0].read_text())
                self.assertIn("runtime", labs[0].read_text().lower())

    def test_chapter_031_restricts_executable_plan_shapes(self):
        sql = (SCRIPTS / "031-index-types-plan.sql").read_text()
        lab = next((ROOT / "labs").glob("031-*-lab.md")).read_text()
        for token in ("shape", "diagnostic", "BEGIN READ ONLY;", "statement_timeout",
                      "lock_timeout", "max_parallel_workers_per_gather",
                      "FORMAT JSON", "ROLLBACK;"):
            self.assertIn(token, sql)
        self.assertIn("031-index-types-setup.sql", lab)

    def test_chapters_032_to_040_have_explicit_non_auto_cleanup(self):
        for ident in ("032", "033", "034", "035", "036", "038", "039"):
            setup = (SQL / f"{ident}-setup.sql").read_text()
            cleanup = (SQL / f"{ident}-cleanup.sql").read_text()
            lab = next((ROOT / "labs").glob(f"{ident}-*-lab.md")).read_text()
            with self.subTest(chapter=ident):
                self.assertNotRegex(setup, r"(?im)^\s*DROP\s+SCHEMA\b")
                for token in ("expected_db", "expected_system_id", "confirm_cleanup",
                              f"{ident}-DROP", "pg_control_system()", r"\if :cleanup_permitted",
                              r"\quit 3"):
                    self.assertIn(token, cleanup)
                self.assertIn(f"-v confirm_cleanup={ident}-DROP", lab)
                self.assertIn("n.nspowner", cleanup)
                self.assertIn("c.relowner", cleanup)
                self.assertIn("NOT EXISTS (SELECT 1 FROM pg_class", cleanup)
                self.assertIn("BEGIN;", cleanup)
                self.assertIn("COMMIT;", cleanup)
                self.assertIn(f"DROP SCHEMA ch{ident};", cleanup)
                expected_table = "orders" if ident in ("032", "033") else "events"
                self.assertIn(f"DROP TABLE ch{ident}.{expected_table};", cleanup)
                self.assertNotRegex(cleanup, r"(?im)^\\s*DROP\\s+SCHEMA\\s+.*CASCADE\\b")
                if ident in ("038", "039"):
                    self.assertIn("pg_inherits", cleanup)

    def test_chapter_033_concurrent_index_workflow_not_wrapped_in_transaction(self):
        sql = (SQL / "033-investigate.sql").read_text()
        self.assertIn("CREATE INDEX CONCURRENTLY", sql)
        self.assertIn("REINDEX INDEX CONCURRENTLY", sql)
        self.assertIn("DROP INDEX CONCURRENTLY", sql)
        self.assertNotRegex(sql, r"(?im)^\s*BEGIN\s*;")
        self.assertIn("ON_ERROR_STOP off", sql)
        self.assertIn("ON_ERROR_STOP on", sql)

    def test_chapter_036_vacuum_and_autovacuum_bounds(self):
        sql = (SQL / "036-investigate.sql").read_text()
        self.assertIn("VACUUM (ANALYZE) ch036.events;", sql)
        self.assertIn("ALTER TABLE ch036.events RESET", sql)
        self.assertNotRegex(sql, r"(?im)^\s*ALTER\s+SYSTEM")
        self.assertNotRegex(sql, r"(?im)^\s*BEGIN\s*;")

    def test_chapter_037_fails_closed_before_creating_fixture(self):
        sql = (SQL / "037-setup.sql").read_text()
        for token in ("expected_system_id", "037-CREATE", "current_database()='ops_lab'",
                      "current_user='lab_admin'", "inet_server_port()=55432",
                      "pg_control_system()", "data_directory", "pg_is_in_recovery()",
                      "to_regnamespace('ch037') IS NULL", r"\if :setup_permitted"):
            self.assertIn(token, sql)
        self.assertIn("BEGIN;", sql)
        self.assertIn("COMMIT;", sql)
        self.assertIn("ANALYZE ch037.orders;", sql)
        self.assertNotIn("IF NOT EXISTS", sql)
        self.assertEqual(len(re.findall(r"(?im)^\s*INSERT\s+INTO", sql)), 1)

    def test_chapter_037_one_time_bounded_mutation_checks(self):
        sql = (SQL / "037-investigate.sql").read_text()
        lab = next((ROOT / "labs").glob("037-*-lab.md")).read_text()
        for token in ("037-CHURN", "expected_system_id",
                      "(SELECT count(*) FROM ch037.orders)=100000",
                      "(SELECT count(*) FROM ch037.orders WHERE status='updated')=0",
                      "UPDATE ch037.orders", "DELETE FROM ch037.orders",
                      "VACUUM (ANALYZE) ch037.orders", r"\if :churn_permitted"):
            self.assertIn(token, sql)
        self.assertNotRegex(sql, r"(?im)^\s*BEGIN\s*;")
        self.assertIn("-v confirm_churn=037-CHURN", lab)
        self.assertIn("90,000 surviving", lab)

    def test_chapter_037_cleanup_has_no_cascade_or_global_deletion(self):
        sql = (SQL / "037-cleanup.sql").read_text()
        lab = next((ROOT / "labs").glob("037-*-lab.md")).read_text()
        for token in ("037-DROP", "expected_system_id", "pg_control_system()",
                      "data_directory", "current_user='lab_admin'",
                      "(SELECT count(*) FROM ch037.orders)=90000",
                      "DROP TABLE ch037.orders;", "DROP SCHEMA ch037;",
                      r"\if :cleanup_permitted", "BEGIN;", "COMMIT;"):
            self.assertIn(token, sql)
        self.assertNotRegex(sql, r"(?im)^\s*DROP\s+SCHEMA\s+.*CASCADE\b")
        self.assertIn("-v confirm_cleanup=037-DROP", lab)
        self.assertIn("004-operations-lab.sh verify", lab)

    def test_chapter_040_stages_check_identity_and_initial_state(self):
        lab = next((ROOT / "labs").glob("040-*-lab.md")).read_text()
        for name, token in (("040-setup.sql", "040-CREATE"),
                            ("040-investigate.sql", "040-LIFECYCLE")):
            sql = (SQL / name).read_text()
            with self.subTest(name=name):
                for check in ("expected_system_id", "pg_control_system()", token,
                              "current_user='lab_admin'", "inet_server_port()=55432",
                              "data_directory", "pg_is_in_recovery()",
                              r"\if :stage_permitted", r"\quit 3"):
                    self.assertIn(check, sql)
                self.assertIn("-v confirm_stage=" + token, lab)
        source = (SQL / "040-investigate.sql").read_text()
        self.assertIn("(SELECT count(*) FROM ch040.events)=12000", source)
        self.assertIn("DETACH PARTITION", source)
        self.assertIn("ATTACH PARTITION", source)

    def test_chapter_040_exact_partition_topology_and_atomic_cleanup(self):
        sql = (SQL / "040-cleanup.sql").read_text()
        lab = next((ROOT / "labs").glob("040-*-lab.md")).read_text()
        for token in ("expected_db", "expected_system_id", "040-DROP",
                      "current_database()='ops_lab'", "current_user='lab_admin'",
                      "data_directory", "pg_control_system()",
                      "(SELECT count(*) FROM ch040.events)=12002",
                      "ch040.events_2026_01", "ch040.events_2026_02",
                      "ch040.events_2026_03", "ch040.events_2026_04",
                      "DROP TABLE ch040.events;", "DROP SCHEMA ch040;",
                      "BEGIN;", "COMMIT;"):
            self.assertIn(token, sql)
        self.assertNotRegex(sql, r"(?im)^\s*DROP\s+SCHEMA\s+.*CASCADE\b")
        self.assertIn("-v confirm_cleanup=040-DROP", lab)
        self.assertIn("independent archive/restore", lab)


if __name__ == "__main__":
    unittest.main()
