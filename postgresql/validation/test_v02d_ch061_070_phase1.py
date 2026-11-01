#!/usr/bin/env python3
"""Offline V02-D Chapter 061-070 phase-one safety contracts (never executes SQL)."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
LABS=ROOT/"labs"
SQL=LABS/"sql"
CH=ROOT/"chapters"

def lab(chapter):
    hits=list(LABS.glob(f"{chapter}-*-lab.md"))
    if len(hits)!=1:
        raise AssertionError(f"Expected one lab for {chapter}, found {hits}")
    return hits[0].read_text(encoding="utf-8")

def script(name):
    return (SQL/name).read_text(encoding="utf-8")


class Review061070PhaseOne(unittest.TestCase):
    def test_ten_chapters_labs_and_navigation(self):
        for n in range(61,71):
            key=f"{n:03d}"
            chapter=list(CH.glob(key+"-*.md"))
            labfile=list(LABS.glob(key+"-*-lab.md"))
            with self.subTest(chapter=key):
                self.assertEqual(len(chapter),1)
                self.assertEqual(len(labfile),1)
                self.assertIn("../labs/"+labfile[0].name,chapter[0].read_text(encoding="utf-8"))
                self.assertIn("runtime",labfile[0].read_text(encoding="utf-8").lower())

    def test_068_setup_refuses_wrong_cluster_or_fixture(self):
        s=script("068-safe-slot-setup.sql")
        for token in ("current_database()='ch068_lab'",
                      "current_user='lab_admin'","inet_server_port()=55432",
                      "inet_server_addr()=inet '127.0.0.1'",
                      "server_version_num","data_directory","pg_control_system()",
                      "NOT pg_is_in_recovery()",
                      "to_regnamespace('ch068') IS NULL",
                      "slot_name='ch068_lab_slot'",
                      "068-CREATE-SLOT",r"\quit 3",r"\if :allowed",
                      "CREATE TABLE ch068.wal_probe","CREATE SCHEMA ch068",
                      "pg_create_physical_replication_slot"):
            self.assertIn(token,s,token)
        self.assertNotIn("IF NOT EXISTS",s)
        self.assertNotIn("DROP ",s)

    def test_068_wal_workload_bounded_once_and_guarded(self):
        s=script("068-safe-wal-workload.sql")
        for required in ("068-GENERATE-WAL","expected_system_id",
                         "current_database()='ch068_lab'","pg_control_system()",
                         "slot_type='physical'","NOT active","statement_timeout",
                         "lock_timeout","generate_series(1,1000)",r"\quit 3"):
            self.assertIn(required,s,required)
        self.assertNotIn("ON CONFLICT",s)
        self.assertNotIn("IF NOT EXISTS",s)
        self.assertNotIn("public.",s)
        self.assertNotIn("DROP ",s)

    def test_068_cleanup_guarded_physical_inactive_and_restrict(self):
        s=script("068-safe-slot-cleanup.sql")
        for required in ("068-DROP-LAB-SLOT","current_database()='ch068_lab'",
                         "pg_control_system()","expected_system_id",
                         "slot_type='physical'","NOT active",r"\if :allowed",
                         r"\quit 3","SELECT pg_drop_replication_slot('ch068_lab_slot')",
                         "DROP TABLE ch068.wal_probe","DROP SCHEMA ch068"):
            self.assertIn(required,s,required)
        self.assertNotIn("CASCADE",s)
        self.assertNotIn("IF EXISTS",s)
        self.assertNotIn("public.",s)

    def test_068_lab_refuses_unscoped_sql_and_unobserved_identity(self):
        s=lab("068")
        for required in ("068-safe-slot-setup.sql",
                         "068-safe-wal-workload.sql",
                         "068-safe-slot-cleanup.sql",
                         "expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID",
                         "confirm_stage=068-CREATE-SLOT",
                         "confirm_stage=068-GENERATE-WAL",
                         "confirm_stage=068-DROP-LAB-SLOT",
                         "dedicated","inactive","Never"):
            self.assertIn(required,s,required)
        self.assertNotIn("DROP TABLE IF EXISTS public.ch068_wal_probe",s)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS public.ch068_wal_probe",s)
        self.assertNotIn("ON CONFLICT (id) DO NOTHING",s)

    def test_069_preserves_prior_config_layer_on_rollback(self):
        s=lab("069")
        for required in ("postgresql.auto.conf","pg_file_settings",
                         "sourcefile","sourceline",
                         "original exact","configuration manager",
                         "NO_GO","reload","rollback"):
            self.assertIn(required.lower(),s.lower(),required)
        self.assertNotIn("ALTER SYSTEM RESET synchronous_standby_names;",s)
        self.assertIn("Do not run an unconditional",s)

    def test_066_070_fail_closed_evidence_not_runtime_verified(self):
        for chapter in ("066","070"):
            doc=lab(chapter)
            self.assertIn("Pending",doc)
            self.assertIn("RPO",doc)
            self.assertIn("RTO",doc)
        self.assertIn("do not promote",lab("070").lower())
        self.assertIn("production",lab("066").lower())


if __name__=="__main__":
    unittest.main()
