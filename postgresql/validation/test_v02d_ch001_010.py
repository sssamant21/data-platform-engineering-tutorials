#!/usr/bin/env python3
"""V02-D Chapters 001-010 contract checks plus Chapter 010 comparator tests.

Static only: does not execute psql, SQL, PostgreSQL server, or OS lifecycle commands.
"""
import csv
import importlib.util
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TEST_MODULE = SCRIPTS / "010-compare-baseline.py"
spec = importlib.util.spec_from_file_location("chapter010_compare_baseline", TEST_MODULE)
comparator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparator)
IDS = [f"{i:03}" for i in range(1, 11)]
EXPECTED = {
    "001": ["001-first-response-snapshot.sql"],
    "002": ["002-architecture-snapshot.sql"],
    "003": [],
    "004": ["004-operations-lab.sh"],
    "005": ["005-safe-catalog-inspection.sql"],
    "006": ["006-path-inventory.sql"],
    "007": ["007-initialization-inventory.sql", "007-drop-lab-databases.sql"],
    "008": ["008-configuration-inspection.sql"],
    "009": ["009-lifecycle-inspection.sql"],
    "010": ["010-capture-baseline.sql", "010-compare-baseline.py",
            "010-drift-inspection.sql"],
}


def build_rows():
    rows = {}
    for name in comparator.NAMES:
        rows[name] = {
            "name": name, "setting": "1", "unit": "", "source": "default",
            "context": "user", "sourcefile": "",
            "pending_restart": "f", "server_major": "18", "is_in_recovery": "f"}
    rows["server_version"]["setting"] = "18.1"
    rows["port"]["setting"] = "55432"
    rows["listen_addresses"]["setting"] = "127.0.0.1"
    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=comparator.FIELDS)
        writer.writeheader()
        writer.writerows(rows.values())


class CurriculumContractTests(unittest.TestCase):
    def test_chapter_lab_pairs_and_source_files(self):
        for ident in IDS:
            chapters = list((ROOT / "chapters").glob(ident + "-*.md"))
            labs = list((ROOT / "labs").glob(ident + "-*-lab.md"))
            with self.subTest(chapter=ident):
                self.assertEqual(len(chapters), 1)
                self.assertEqual(len(labs), 1)
                self.assertIn("(../labs/" + labs[0].name + ")", chapters[0].read_text())
                for script in EXPECTED[ident]:
                    self.assertTrue((SCRIPTS / script).is_file(), script)
                    self.assertIn(script, labs[0].read_text())

    def test_chapter007_destructive_cleanup_guards(self):
        path = SCRIPTS / "007-drop-lab-databases.sql"
        script = path.read_text()
        lab = next((ROOT / "labs").glob("007-*-lab.md")).read_text()
        for token in ["expected_system_id", "confirm_cleanup", "007-DROP-DATABASES",
                      "pg_control_system()", "datlocprovider", "pg_get_userbyid(d.datdba)",
                      "pg_stat_activity", "current_database() = 'postgres'",
                      "pg_is_in_recovery()", "inet_server_port() = 55432",
                      r"\if :cleanup_permitted", r"\quit 3"]:
            with self.subTest(control=token):
                self.assertIn(token, script)
        self.assertIn("-f postgresql/scripts/007-drop-lab-databases.sql", lab)
        self.assertIsNone(re.search(r"-c\s+['\"]DROP\s+DATABASE", lab, re.I))

    def test_chapter010_capture_avoids_restricted_data_path(self):
        capture = (SCRIPTS / "010-capture-baseline.sql").read_text()
        self.assertIn("'server_version'", capture)
        self.assertNotIn("'data_directory'", capture)
        self.assertIn("server_version", comparator.NAMES)
        self.assertNotIn("data_directory", comparator.NAMES)
        self.assertEqual(len(comparator.NAMES), 12)

    def test_baseline_equal_and_alternative_role_visibility(self):
        approved = build_rows()
        observed = {k: dict(v) for k, v in approved.items()}
        self.assertEqual(comparator.compare(approved, observed), [])
        # Restricted applications may not see sourcefile; the same role's
        # snapshot must be compared to the same privilege profile.
        self.assertTrue(all(x["sourcefile"] == "" for x in approved.values()))

    def test_detect_value_and_provenance_drift(self):
        approved = build_rows()
        observed = {k: dict(v) for k, v in approved.items()}
        observed["work_mem"]["setting"] = "8192"
        observed["work_mem"]["source"] = "client"
        result = comparator.compare(approved, observed)
        self.assertTrue(any("work_mem.setting" in x for x in result), result)
        self.assertTrue(any("work_mem.source" in x for x in result), result)

    def test_pending_restart_always_fails_acceptance(self):
        approved = build_rows()
        observed = {k: dict(v) for k, v in approved.items()}
        observed["shared_buffers"]["pending_restart"] = "t"
        self.assertTrue(any("PENDING RESTART" in x for x in comparator.compare(approved, observed)))
        approved["shared_buffers"]["pending_restart"] = "t"
        with self.assertRaisesRegex(ValueError, "pending restart"):
            comparator.compare(approved, observed)

    def test_csv_round_trip_and_missing_setting_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "baseline.csv"
            rows = build_rows()
            write_csv(target, rows)
            self.assertEqual(set(comparator.read_snapshot(target)), comparator.NAMES)
            rows.pop("port")
            write_csv(target, rows)
            with self.assertRaisesRegex(ValueError, "missing settings"):
                comparator.read_snapshot(target)

    def test_wrong_major_and_duplicate_setting_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "baseline.csv"
            rows = build_rows()
            rows["port"]["server_major"] = "17"
            write_csv(target, rows)
            with self.assertRaisesRegex(ValueError, "major 18"):
                comparator.read_snapshot(target)
            rows["port"]["server_major"] = "18"
            # Duplicate rows must not silently overwrite prior evidence.
            with target.open("w", newline="", encoding="utf-8") as fp:
                writer = csv.DictWriter(fp, fieldnames=comparator.FIELDS)
                writer.writeheader()
                writer.writerows(rows.values())
                writer.writerow(rows["port"])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                comparator.read_snapshot(target)


if __name__ == "__main__":
    unittest.main()
