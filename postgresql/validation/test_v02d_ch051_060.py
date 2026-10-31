#!/usr/bin/env python3
"""V02-D Chapters 051-060: safe security and connection-pool static contracts.

No PostgreSQL connections, PgBouncer calls, role changes, SQL execution or load tests.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LABS = ROOT / "labs"
SQL = LABS / "sql"

def source(name):
    return (SQL / name).read_text(encoding="utf-8")

def lab(number):
    paths = list(LABS.glob(number + "-*-lab.md"))
    if len(paths) != 1:
        raise AssertionError(f"Expected exactly one lab for {number}: {paths}")
    return paths[0].read_text(encoding="utf-8")

class Review051060(unittest.TestCase):
    def test_all_ten_chapter_lab_pairs_and_navigation(self):
        for n in range(51, 61):
            ident = str(n).zfill(3)
            chapters = list((ROOT / "chapters").glob(ident + "-*.md"))
            labs = list(LABS.glob(ident + "-*-lab.md"))
            with self.subTest(chapter=ident):
                self.assertEqual(len(chapters), 1)
                self.assertEqual(len(labs), 1)
                self.assertIn("../labs/" + labs[0].name, chapters[0].read_text())
                self.assertIn("runtime", lab(ident).lower())

    def test_051_053_054_060_privileged_sql_is_cluster_identity_guarded(self):
        cases = [
            ("051-provision.sql", "ch051_lab", "051-PROVISION"),
            ("053-provision.sql", "ch053_lab", "053-PROVISION"),
            ("054-events.sql", "ch054_lab", "054-GENERATE-EVENTS"),
            ("060-fixture.sql", "ch060_lab", "060-CREATE-IDEMPOTENCY"),
        ]
        for file, db, token in cases:
            src = source(file)
            with self.subTest(file=file):
                for required in (
                    "expected_system_id", r"\if :{?confirm_stage}", token,
                    "current_database()='" + db + "'",
                    "current_user='lab_admin'",
                    "inet_server_port()=55432",
                    "pg_control_system()",
                    "data_directory", "pg_is_in_recovery()",
                    r"\if :stage_permitted", "SELECT 1/0 AS refusal_nonzero;",
                    "BEGIN;", "COMMIT;", "lock_timeout", "statement_timeout",
                ):
                    self.assertIn(required, src, required)
                self.assertIn("confirm_stage=" + token, lab(db[2:5]))
                self.assertIn("expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID",
                              lab(db[2:5]))

    def test_051_roles_and_privilege_validation_exit_nonzero(self):
        provision = source("051-provision.sql")
        verify = source("051-verify.sql")
        self.assertIn("ALTER DEFAULT PRIVILEGES FOR ROLE ch051_owner", provision)
        self.assertIn("WITH INHERIT TRUE, SET FALSE", provision)
        self.assertIn("SET ROLE ch051_owner", provision)
        self.assertIn("pg_auth_members", verify)
        self.assertIn("has_table_privilege", verify)
        self.assertIn("RAISE EXCEPTION 'FAIL: Chapter 051", verify)
        self.assertIn("m.inherit_option", verify)
        self.assertIn("NOT m.set_option", verify)
        self.assertIn("ch051.after_default_grants", verify)

    def test_052_hba_tls_and_scram_negative_tests(self):
        doc = lab("052").lower()
        for required in ("verify-full", "scram", "pg_hba_file_rules",
                         "wrong hostname", "hostssl", "rollback",
                         "break-glass"):
            self.assertIn(required, doc)
        self.assertIn("pg_stat_ssl", source("052-inspect.sql"))

    def test_053_rls_force_security_definer_and_fail_on_cross_tenant(self):
        src = source("053-provision.sql")
        verify = source("053-verify.sql")
        for required in ("SECURITY DEFINER", "SET search_path = pg_catalog, pg_temp",
                         "session_user", "FORCE ROW LEVEL SECURITY", "WITH CHECK",
                         "ch053.tenant_mapping", "NOBYPASSRLS"):
            self.assertIn(required, src)
        for required in ("SET SESSION AUTHORIZATION ch053_tenant_a",
                         "SET SESSION AUTHORIZATION ch053_tenant_b",
                         "EXCEPTION WHEN insufficient_privilege",
                         "Tenant A cross-tenant read",
                         "Tenant B cross-tenant update unexpectedly succeeded"):
            self.assertIn(required, verify)
        self.assertIn("superuser", lab("053").lower())

    def test_054_auditing_stages_and_log_config_limitations(self):
        src = source("054-events.sql")
        self.assertIn("CREATE ROLE ch054_auditor", src)
        self.assertIn("CREATE SCHEMA ch054", src)
        self.assertNotIn("IF NOT EXISTS", src)
        doc = lab("054").lower()
        self.assertIn("only if", doc)
        self.assertIn("log", doc)
        self.assertIn("pg_stat_ssl", source("054-inspect.sql"))

    def test_055_does_not_pass_with_missing_roles_or_unreadable_hba(self):
        s = source("055-assertions.sql")
        for required in ("<> 4", "required security lab identities are missing",
                         "NOT EXISTS (SELECT 1 FROM pg_hba_file_rules)",
                         "pg_hba.conf parse errors detected",
                         "rolbypassrls", "RAISE EXCEPTION"):
            self.assertIn(required, s)
        self.assertIn("NOT ACCEPTED", lab("055"))

    def test_056_057_pooling_session_and_connection_budget(self):
        for n in ("056", "057"):
            doc = lab(n)
            self.assertIn("SHOW POOLS;", doc)
            self.assertIn("SHOW STATS;", doc)
            self.assertIn("max_connections", source(n + "-" +
                              ("connections.sql" if n=="056" else "capacity.sql")))
        doc = lab("057")
        for required in ("ON COMMIT DROP", "SET LOCAL", "transaction pooling",
                         "max_prepared_statements", "pg_advisory_xact_lock"):
            self.assertIn(required, doc)

    def test_058_059_bounded_incident_and_monitoring_contract(self):
        doc58 = lab("058")
        self.assertIn("lock_timeout='3s'", doc58)
        self.assertIn("ROLLBACK;", doc58)
        self.assertIn("55P03", doc58)
        self.assertIn("SHOW CLIENTS;", doc58)
        self.assertNotIn("pg_terminate_backend(", source("058-diagnostics.sql"))
        doc59 = lab("059")
        self.assertIn("059-alerts.example.yml", doc59)
        self.assertIn("exporter unavailability", doc59)
        self.assertIn("pg_stat_database", source("059-monitoring.sql"))

    def test_060_fixture_once_and_idempotency_assertion(self):
        s = source("060-fixture.sql")
        self.assertIn("to_regnamespace('ch060') IS NULL", s)
        self.assertIn("CREATE SCHEMA ch060", s)
        self.assertIn("CREATE TABLE ch060.requests", s)
        self.assertNotIn("IF NOT EXISTS", s)
        self.assertEqual(s.count("VALUES ('baseline-001','sample')"), 2)
        self.assertEqual(s.count("ON CONFLICT (request_id) DO NOTHING"), 2)
        self.assertIn("count(*) FROM ch060.requests", s)
        self.assertIn("RAISE EXCEPTION 'FAIL: idempotency fixture", s)
        self.assertIn("confirm_stage=060-CREATE-IDEMPOTENCY", lab("060"))
        self.assertIn("one", lab("060").lower())


if __name__ == "__main__":
    unittest.main()
