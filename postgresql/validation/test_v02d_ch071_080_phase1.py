#!/usr/bin/env python3
"""PostgreSQL V02-D Chapter 071-080 phase 1 offline safety contracts.

No PostgreSQL servers, Docker containers, HA failures or credentials are used.
Source inspection cannot prove operational safety or human authorization.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
LABS=ROOT/"labs"
SQL=LABS/"sql"
CH=ROOT/"chapters"

def chapter_file(n,folder):
    hits=list(folder.glob(f"{n:03d}-*.md"))
    if len(hits)!=1:
        raise AssertionError(f"Expected one {n:03d} chapter in {folder}, got {hits}")
    return hits[0]

def sql(n,name):
    return (SQL/f"{n:03d}-{name}.sql").read_text(encoding="utf-8")

class PhaseOneSafety(unittest.TestCase):
    def test_all_ten_chapters_and_labs_exist_and_are_linked(self):
        for n in range(71,81):
            with self.subTest(chapter=n):
                c=chapter_file(n,CH)
                l=chapter_file(n,LABS)
                self.assertIn("../labs/"+l.name,c.read_text(encoding="utf-8"))
                self.assertIn("Runtime",l.read_text(encoding="utf-8"))

    def test_read_only_inspections_have_no_mutating_sql(self):
        for n,filename in (
            (71,"ha-automation-inspect"),(72,"ha-observability-inspect"),
            (73,"multi-zone-ha-inspect"),(74,"cross-region-dr-inspect"),
            (75,"ha-dr-acceptance-inspect"),(76,"security-roles-and-privileges-inspect"),
            (77,"authentication-tls-inspect"),(78,"rls-and-audit-inspect"),
            (79,"encryption-secrets-hardening-inspect"),(80,"security-incident-inspect"),
        ):
            with self.subTest(sql=filename):
                text=sql(n,filename)
                for forbidden in ("CREATE ROLE ","DROP ROLE ","ALTER SYSTEM ","pg_promote(",
                                  "pg_drop_replication_slot(","CREATE DATABASE ",
                                  "DROP DATABASE ","pg_terminate_backend("):
                    self.assertNotIn(forbidden,text.upper() if forbidden.isupper() else text)

    def test_076_078_fixtures_are_identity_and_ownership_gated(self):
        for n,name in ((76,"security-role-fixture"),(78,"rls-fixture")):
            s=sql(n,name)
            with self.subTest(chapter=n):
                self.assertTrue(s.startswith("-- Chapter"))
                self.assertIn(r"\set ON_ERROR_STOP on",s)
                self.assertIn(r"\if :{?expected_system_id}",s)
                self.assertIn(r"\if :{?expected_lab_pgdata}",s)
                self.assertIn(r"\if :{?confirm_stage}",s)
                for guard in ("current_database()='postgres'",
                              "current_user='lab_admin'",
                              "inet_server_addr()=inet '127.0.0.1'",
                              "inet_server_port()=55432","server_version_num",
                              "current_setting('data_directory')=:'expected_lab_pgdata'",
                              "pg_control_system()","NOT pg_is_in_recovery()",
                              f"{n:03d}-CREATE-LAB-FIXTURE",
                              f"datname='ch{n:03d}_lab'",
                              f"left(rolname,6)='ch{n:03d}_'",
                              "NOT EXISTS",r"\gset",r"\if :allowed",
                              "RAISE EXCEPTION",r"\if :scoped"):
                    self.assertIn(guard,s,guard)
                # Check executable DDL and its ORDER, not comments.
                first_role=s.index("\nCREATE ROLE ch"+str(n).zfill(3)+"_owner")
                first_db=s.index("\nCREATE DATABASE ch"+str(n).zfill(3)+"_lab")
                self.assertGreater(first_role,s.index(r"\if :allowed"))
                self.assertGreater(first_db,first_role)
                self.assertGreater(s.index("\nCREATE SCHEMA "),s.index(r"\if :scoped"))
                self.assertEqual(1,s.count("\nCREATE ROLE ch"+str(n).zfill(3)+"_owner"))
                self.assertEqual(1,s.count("\nCREATE DATABASE ch"+str(n).zfill(3)+"_lab"))
                self.assertEqual(5,s.count("RAISE EXCEPTION"))
                self.assertEqual(5,s.count("DO "+chr(36)*2+" BEGIN RAISE EXCEPTION"))
                self.assertIn("primary"+chr(36)+"\x27",s)
                self.assertNotIn("END "+chr(36)+";",s)
                self.assertIn(f"current_database()='ch{n:03d}_lab'",s)
                self.assertNotIn("DROP ROLE",s)
                self.assertNotIn("DROP DATABASE",s)
                self.assertNotIn("CREATE ROLE IF NOT EXISTS",s)

    def test_076_078_docs_require_observed_lab_root_and_stage(self):
        for n in (76,78):
            l=chapter_file(n,LABS).read_text(encoding="utf-8")
            for token in ("PG_LAB_ROOT","LAB_MARKER","127.0.0.1",
                          "expected_system_id=REPLACE_WITH_OBSERVED_SYSTEM_ID",
                          "expected_lab_pgdata=$PG_LAB_ROOT/primary",
                          f"confirm_stage={n:03d}-CREATE-LAB-FIXTURE",
                          "lab_admin","ON_ERROR_STOP=1"):
                with self.subTest(n=n,token=token):
                    self.assertIn(token,l)
            self.assertNotIn(f"-U postgres -d postgres -f postgresql/labs/sql/{n:03d}",l)

    def test_075_ha_marker_does_not_adopt_old_data(self):
        l=chapter_file(75,LABS).read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE public.ch075_probe",l)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS public.ch075_probe",l)
        self.assertNotIn("ON CONFLICT DO NOTHING",l)
        self.assertIn("verify endpoint",l)
        self.assertIn("NO_GO",l)

    def test_071_075_failover_stays_fencing_gated(self):
        for n in range(71,76):
            l=chapter_file(n,LABS).read_text(encoding="utf-8").lower()
            with self.subTest(chapter=n):
                self.assertIn("fenc",l)
                self.assertIn("lab",l)
                self.assertIn("pending",l)
        self.assertIn("not verified",chapter_file(75,LABS).read_text(encoding="utf-8").lower())

    def test_077_tls_negative_paths_and_078_rls_require_live_tests(self):
        auth=chapter_file(77,LABS).read_text(encoding="utf-8")
        rls=chapter_file(78,LABS).read_text(encoding="utf-8")
        for token in ("sslmode=verify-full","untrusted CA","mismatched hostname",
                      "sslmode=disable","pg_hba"):
            self.assertIn(token,auth)
        for token in ("BYPASSRLS","SQLSTATE","tenant","FORCE ROW LEVEL SECURITY"):
            self.assertIn(token,rls)

    def test_security_ha_certification_remains_pending(self):
        for n in range(71,81):
            l=chapter_file(n,LABS).read_text(encoding="utf-8").lower()
            self.assertIn("runtime",l)
            self.assertIn("pending",l)


if __name__=="__main__":
    unittest.main()
