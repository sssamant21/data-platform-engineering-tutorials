#!/usr/bin/env python3
"""V02-D Chapters 041-050: static backup, PITR, slot, HA and DR safety contracts.

Does not call psql, pg_basebackup, pg_rewind, promote or drop anything.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
LABS=ROOT/"labs"
SQL=LABS/"sql"
IDS=[f"{n:03}" for n in range(41,51)]

def lab(n):
    files=list(LABS.glob(n+"-*-lab.md"))
    if len(files)!=1:
        raise ValueError(f"Expected one lab for {n}, got {len(files)}")
    return files[0].read_text(encoding="utf-8")

def sql(name):
    return (SQL/name).read_text(encoding="utf-8")

class BackupReplication041050(unittest.TestCase):
    def test_chapters_and_navigation(self):
        for n in IDS:
            chapters=list((ROOT/"chapters").glob(n+"-*.md"))
            with self.subTest(chapter=n):
                self.assertEqual(len(chapters),1)
                self.assertIn("../labs/"+next(LABS.glob(n+"-*-lab.md")).name,
                              chapters[0].read_text(encoding="utf-8"))
                self.assertIn("Runtime",lab(n))

    def test_041_042_dump_restore_validation(self):
        for n in ("041","042"):
            content=lab(n)
            with self.subTest(chapter=n):
                for token in ("pg_dump -Fc","pg_restore --list","pg_restore --exit-on-error",
                              f"{n}-fixture.sql", f"{n}-verify.sql","source","restore"):
                    self.assertIn(token,content)
                fixture=sql(n+"-fixture.sql")
                verify=sql(n+"-verify.sql")
                self.assertIn("CREATE TABLE",fixture)
                self.assertIn("INSERT INTO",fixture)
                self.assertIn("count(*)",verify)
                self.assertIn("md5(string_agg",verify)

    def test_043_manifest_and_044_continuous_wal_contract(self):
        self.assertIn("pg_verifybackup",lab("043"))
        self.assertIn("pg_basebackup",lab("043"))
        self.assertIn("new empty backup directory",lab("043"))
        content=lab("044")
        for required in ("restore_command","recovery.signal",
                         "continuous WAL", "isolated", "timeline"):
            self.assertIn(required,content)
        self.assertIn("pg_stat_archiver",sql("044-preflight.sql"))
        self.assertIn("pg_current_wal_lsn()",sql("044-marker.sql"))
        marker=sql("044-marker.sql")
        for expected in ("expected_data_directory","expected_operator",
                         "expected_system_id","044-MARKER","pg_control_system()",
                         r"\if :stage_permitted","BEGIN;","COMMIT;"):
            self.assertIn(expected,marker)
        self.assertNotIn("IF NOT EXISTS",marker)
        self.assertIn("confirm_stage=044-MARKER",lab("044"))

    def test_045_incident_restricted_to_source_identity(self):
        source=sql("045-incident.sql")
        for required in (r"\if :{?expected_db}", r"\if :{?expected_system_id}",
                         r"\if :{?expected_source_data_directory}",
                         r"\if :{?expected_operator}", r"\if :{?confirm_incident}",
                         "current_user = :'expected_operator'",
                         "current_setting('data_directory') = :'expected_source_data_directory'",
                         "pg_control_system()", "045-INCIDENT", r"\if :incident_permitted",
                         "SELECT 1/0 AS refusal_nonzero;", "UPDATE ch045.orders"):
            self.assertIn(required,source)
        doc=lab("045")
        self.assertIn("expected_source_data_directory=",doc)
        for name,token in (("045-fixture.sql","045-CREATE-FIXTURE"),
                           ("045-good-marker.sql","045-GOOD-MARKER")):
            stage=sql(name)
            with self.subTest(name=name):
                for expected in ("expected_data_directory","expected_operator",
                                 "expected_system_id",token,
                                 "pg_control_system()",r"\if :stage_permitted"):
                    self.assertIn(expected,stage)
                self.assertIn("confirm_stage="+token,doc)
        self.assertIn("BEGIN;",sql("045-fixture.sql"))
        self.assertIn("COMMIT;",sql("045-fixture.sql"))
        self.assertIn("expected_operator=",doc)

    def test_045_recovery_verification_has_exit_code_failure(self):
        source=sql("045-verify.sql")
        for required in ("expected_recovery_data_directory","expected_system_id",
                         "045-VERIFY-RECOVERY", "pg_control_system()",
                         "recovery_accepted", r"\if :recovery_accepted",
                         "SELECT 1/0 AS refusal_nonzero;", "status='corrupted'", "status='valid'",
                         "marker_name='known-good'"):
            self.assertIn(required,source)
        doc=lab("045")
        self.assertIn("-v confirm_recovery=045-VERIFY-RECOVERY",doc)
        self.assertIn("RECOVERY_HOST",doc)
        self.assertIn("nonzero",doc)

    def test_046_backup_monitoring_read_only(self):
        content=lab("046")
        self.assertIn("046-monitor.sh",content)
        for bad in ("DROP DATABASE","pg_terminate_backend(","DELETE FROM"):
            self.assertNotIn(bad,sql("046-monitor.sql"))
        self.assertIn("pg_stat_archiver",sql("046-monitor.sql"))
        self.assertIn("pg_stat_progress_basebackup",sql("046-monitor.sql"))

    def test_004_topology_slot_capacity_and_checkpoint_retention(self):
        """Fail static CI if the disposable topology cannot run Chapter 047."""
        script=(ROOT/"scripts"/"004-operations-lab.sh").read_text(encoding="utf-8")
        cap=re.search(r"(?m)^max_replication_slots = (\d+)$",script)
        bounded=re.search(r"(?m)^max_slot_wal_keep_size = '(\d+)MB'$",script)
        self.assertIsNotNone(cap,"Chapter 004 must explicitly configure slots")
        self.assertIsNotNone(bounded,"Chapter 004 must bound slot WAL retention")
        self.assertGreaterEqual(int(cap.group(1)),1)
        self.assertGreater(int(bounded.group(1)),0)
        self.assertLessEqual(int(bounded.group(1)),512)
        self.assertIn('SHOW max_replication_slots',script)
        self.assertIn("name='max_slot_wal_keep_size'",script)
        self.assertIn('for port in 55432 55433 55434',script)
        slot=sql("047-create-lab-slot.sql")
        for guard in ("current_setting('max_replication_slots')::integer >= 1",
                      "(SELECT count(*) FROM pg_replication_slots) < current_setting('max_replication_slots')::integer",
                      "name='max_slot_wal_keep_size'", "unit='MB'",
                      "setting::integer BETWEEN 1 AND 512"):
            self.assertIn(guard,slot)
        guide=lab("047")
        self.assertIn("max_replication_slots",guide)
        self.assertIn("max_slot_wal_keep_size",guide)
        self.assertIn("checkpoint",guide.lower())

    def test_guarded_refusals_produce_nonzero_psql_exit(self):
        # ON_ERROR_STOP must encounter a real SQL error, not a normal \\quit.
        guarded = ("044-marker.sql", "045-fixture.sql", "045-good-marker.sql",
                   "045-incident.sql", "045-verify.sql", "047-create-lab-slot.sql",
                   "047-generate-wal.sql", "047-cleanup.sql",
                   "048-workload.sql", "048-cleanup.sql")
        for name in guarded:
            with self.subTest(name=name):
                script=sql(name)
                self.assertIn(r"\set ON_ERROR_STOP on",script)
                self.assertNotIn(r"\quit 3",script)
                self.assertIn("SELECT 1/0 AS refusal_nonzero;",script)
        for number in ("032","033","034","035","036","038","039","040"):
            with self.subTest(chapter=number):
                script=sql(number+"-cleanup.sql")
                self.assertIn(r"\set ON_ERROR_STOP on",script)
                self.assertNotIn(r"\quit 3",script)
                self.assertIn("SELECT 1/0 AS refusal_nonzero;",script)

    def test_047_slot_creation_and_one_time_wal_fixture(self):
        for file,stage in (("047-create-lab-slot.sql","047-CREATE-SLOT"),
                           ("047-generate-wal.sql","047-GENERATE-WAL")):
            content=sql(file)
            with self.subTest(file=file):
                for token in ("expected_system_id",r"\if :{?confirm_stage}",
                              stage,"pg_control_system()", "inet_server_port()=55432",
                              "current_user='lab_admin'", "data_directory",
                              "pg_is_in_recovery()",r"\if :stage_permitted","SELECT 1/0 AS refusal_nonzero;"):
                    self.assertIn(token,content)
        fixture=sql("047-generate-wal.sql")
        self.assertIn("CREATE SCHEMA ch047",fixture)
        self.assertNotIn("IF NOT EXISTS",fixture)
        self.assertNotIn("ON CONFLICT",fixture)
        self.assertIn("generate_series(1,2000)",fixture)
        doc=lab("047")
        self.assertIn("confirm_stage=047-CREATE-SLOT",doc)
        self.assertIn("confirm_stage=047-GENERATE-WAL",doc)

    def test_047_cleanup_exact_slot_and_no_cascade(self):
        content=sql("047-cleanup.sql")
        for token in ("expected_db", "expected_system_id", "047-DROP",
                      "current_database()='ops_lab'", "current_user='lab_admin'",
                      "pg_control_system()", "NOT active",
                      "n.nspowner", "c.relowner",
                      "(SELECT count(*) FROM ch047.wal_fixture)=2000",
                      "DROP TABLE ch047.wal_fixture;", "DROP SCHEMA ch047;",
                      "pg_drop_replication_slot('ch047_lab_physical')",
                      "BEGIN;", "COMMIT;"):
            self.assertIn(token,content)
        self.assertNotRegex(content,r"(?im)^\s*DROP\s+SCHEMA\s+.*CASCADE")
        self.assertLess(content.index("DROP SCHEMA ch047;"),
                        content.index("pg_drop_replication_slot('ch047_lab_physical')"))
        self.assertIn("-v confirm_cleanup=047-DROP",lab("047"))

    def test_048_workload_restrictions_and_cleanup(self):
        content=sql("048-workload.sql")
        for token in ("expected_system_id", "048-WORKLOAD",
                      "current_user='lab_admin'","inet_server_port()=55432",
                      "to_regnamespace('ch048') IS NULL",
                      "CREATE SCHEMA ch048", "generate_series(1,5000)",
                      "COMMIT;", r"\if :stage_permitted"):
            self.assertIn(token,content)
        self.assertNotIn("IF NOT EXISTS",content)
        self.assertNotIn("ON CONFLICT",content)
        cleanup=sql("048-cleanup.sql")
        for token in ("048-DROP","expected_system_id", "current_database()='ops_lab'",
                      "n.nspowner","c.relowner","(SELECT count(*) FROM ch048.events)=5000",
                      "DROP TABLE ch048.events;","DROP SCHEMA ch048;","BEGIN;","COMMIT;"):
            self.assertIn(token,cleanup)
        self.assertNotRegex(cleanup,r"(?im)^\s*DROP\s+SCHEMA\s+.*CASCADE")
        doc=lab("048")
        self.assertIn("confirm_stage=048-WORKLOAD",doc)
        self.assertIn("confirm_cleanup=048-DROP",doc)
        self.assertIn("-p 55433",doc)

    def test_049_050_manual_fencing_rewind_and_dr_acceptance(self):
        for ch in ("049","050"):
            doc=lab(ch).lower()
            for token in ("fenc","pg_rewind","standby.signal","rejoin"):
                self.assertIn(token,doc)
            self.assertNotRegex(doc,r"(?im)^\s*(?:pg_ctl\s+promote|select\s+pg_promote\()")
        self.assertIn("dry-run",lab("049"))
        self.assertIn("RPO/RTO",lab("050"))
        self.assertIn("PITR",lab("050"))
        self.assertIn("mandatory",lab("050").lower())


if __name__=="__main__":
    unittest.main()
