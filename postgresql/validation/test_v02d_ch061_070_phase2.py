#!/usr/bin/env python3
"""V02-D Chapters 061-070 phase-two static contracts. No DB connections."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
LABS=ROOT/"labs"
SQL=LABS/"sql"

def lab(n):
    files=list(LABS.glob(str(n).zfill(3)+"-*-lab.md"))
    if len(files)!=1:
        raise AssertionError(f"Expected one lab for Chapter {n}; got {files}")
    return files[0].read_text(encoding="utf-8")

def src(name):
    return (SQL/name).read_text(encoding="utf-8")


class Chapters061070PhaseTwo(unittest.TestCase):
    def test_064_066_070_one_time_fixtures_guarded(self):
        for chapter,name,db,namespace,token in (
            ("064","064-fixture.sql","ch064_lab","ch064","064-ONE-TIME-FIXTURE"),
            ("066","066-dr-fixture.sql","ch066_lab","ch066","066-ONE-TIME-FIXTURE"),
            ("070","070-one-time-marker-fixture.sql","ch070_lab","ch070","070-ONE-TIME-MARKER"),
        ):
            script=src(name)
            with self.subTest(file=name):
                for requirement in (
                    r"\set ON_ERROR_STOP on",r"\if :{?expected_system_id}",
                    r"\if :{?expected_lab_data_directory}",
                    r"\if :{?expected_lab_role}",r"\if :{?confirm_stage}",
                    "current_database()='"+db+"'",
                    "current_user=:'expected_lab_role'",
                    "current_setting('data_directory')=:'expected_lab_data_directory'",
                    "current_setting('server_version_num')::integer BETWEEN 180000 AND 189999",
                    "NOT pg_is_in_recovery()",
                    "pg_control_system()","c.system_identifier::text=:'expected_system_id'",
                    "to_regnamespace('"+namespace+"') IS NULL",
                    token,r"\gset",r"\if :allowed",r"\quit 3",
                    "BEGIN;","COMMIT;","SET LOCAL lock_timeout",
                ):
                    self.assertIn(requirement,script,requirement)
                self.assertNotIn("IF NOT EXISTS",script)
                self.assertNotIn("ON CONFLICT",script)
                self.assertNotIn("DROP ",script)

    def test_064_archive_and_pitr_targets_have_explicit_offsets(self):
        text=lab("064")
        for term in (
            "expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID",
            "expected_lab_data_directory=REPLACE_WITH_OBSERVED_LAB_PGDATA",
            "expected_lab_role=REPLACE_WITH_OBSERVED_LAB_ROLE",
            "confirm_stage=064-ONE-TIME-FIXTURE",
            "064-fixture.sql","set -euo pipefail",
            "pg_verifybackup /backups/ch064/base001",
            "after_first_commit_utc_with_offset",
            "after_second_commit_utc_with_offset",
            "full explicit UTC offset",
            "recovery_target_time",
            "recovery_target_inclusive=false",
            "archive",
        ):
            self.assertIn(term,text,term)
        self.assertNotIn("clock_timestamp() AT TIME ZONE 'UTC'",text)
        self.assertNotIn("CREATE SCHEMA IF NOT EXISTS",src("064-fixture.sql"))

    def test_066_dr_acceptance_is_not_false_positive(self):
        text=lab("066")
        for term in (
            "confirm_stage=066-ONE-TIME-FIXTURE",
            "expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID",
            "expected_lab_data_directory=REPLACE_WITH_OBSERVED_LAB_PGDATA",
            "expected_lab_role=REPLACE_WITH_OBSERVED_LAB_ROLE",
            "066-dr-fixture.sql","set -euo pipefail",
            "test ! -e /backups/ch066/base001",
            "pg_verifybackup /backups/ch066/base001",
            "before the second transaction begins",
            "explicit UTC offset",
            "DR03 FAIL",
        ):
            self.assertIn(term,text,term)
        self.assertNotIn("CREATE SCHEMA IF NOT EXISTS",src("066-dr-fixture.sql"))
        self.assertNotIn("ON CONFLICT",src("066-dr-fixture.sql"))

    def test_070_switched_primary_uses_one_time_marker_and_external_fence(self):
        text=lab("070")
        for term in (
            "070-one-time-marker-fixture.sql",
            "confirm_stage=070-ONE-TIME-MARKER",
            "expected_lab_data_directory=REPLACE_WITH_OBSERVED_LAB_PGDATA",
            "expected_lab_role=REPLACE_WITH_OBSERVED_LAB_ROLE",
            "expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID",
            "independently verified quorum and fencing",
            "tabletop exercise",
            "NOT VERIFIED",
        ):
            self.assertIn(term,text,term)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS public.ch070_marker",text)
        self.assertNotIn("ON CONFLICT DO NOTHING",src("070-one-time-marker-fixture.sql"))
        self.assertIn("INSERT INTO ch070.markers",src("070-one-time-marker-fixture.sql"))

    def test_061_backup_aborts_on_existing_archive_and_failures(self):
        text=lab("061")
        self.assertIn("Test-Path .\\backups\\ch061\\source.dump",text)
        self.assertIn("if ($LASTEXITCODE -ne 0) { throw 'Backup failed' }",text)
        self.assertIn("if ($LASTEXITCODE -ne 0) { throw 'Isolated restore failed' }",text)

    def test_062_dump_and_restore_check_exit_codes_and_collisions(self):
        text=lab("062")
        for term in ("Test-Path .\\backups\\ch062\\source.dump",
                     "Test-Path .\\backups\\ch062\\source.dir",
                     "Custom archive backup failed",
                     "Custom archive TOC verification failed",
                     "Directory archive backup failed","Isolated restore failed"):
            self.assertIn(term,text)

    def test_063_basebackup_exists_and_restore_queries_checked(self):
        text=lab("063")
        for term in ("Test-Path .\\backups\\ch063\\base001",
                     "Backup verification failed","Isolated restored server not ready",
                     "Restored database query failed","Restored database stop failed",
                     "pg_verifybackup"):
            self.assertIn(term,text)

    def test_065_uses_unique_retention_artifacts(self):
        text=lab("065")
        self.assertIn("if (Test-Path $out)",text)
        self.assertIn("Retention dependency",text)
        self.assertIn("dry run only",text)
        self.assertNotIn("Remove-Item -Recurse",text)

    def test_067_standby_clone_refuses_active_pgdata(self):
        text=lab("067")
        for term in ("Never run pg_basebackup into an active PGDATA",
                     "standby stopped","-R", "pg_is_in_recovery()",
                     "Do not promote"):
            self.assertIn(term,text)

    def test_070_no_operational_mutation_in_preflight(self):
        text=src("070-ha-preflight.sql")
        for forbidden in ("pg_promote", "pg_terminate_backend","pg_drop_replication_slot",
                          "CREATE TABLE","DROP TABLE", "ALTER SYSTEM"):
            self.assertNotIn(forbidden,text)

    def test_061_070_runtime_and_certification_remain_pending(self):
        for number in range(61,71):
            content=lab(number).lower()
            with self.subTest(chapter=number):
                self.assertIn("runtime",content)
                self.assertIn("pending",content)

    def test_explicit_safety_refusal_and_no_production_operations(self):
        for n in ("064","066","070"):
            txt=lab(n).lower()
            self.assertIn("production",txt)
            self.assertIn("lab",txt)
        for name in ("064-fixture.sql","066-dr-fixture.sql","070-one-time-marker-fixture.sql"):
            self.assertIn("REFUSED",src(name))
            self.assertNotIn("CASCADE",src(name))


if __name__=="__main__":
    unittest.main()
