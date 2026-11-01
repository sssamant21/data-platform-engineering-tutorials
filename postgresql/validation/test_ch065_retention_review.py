#!/usr/bin/env python3
"""Synthetic-only Chapter 065 retention guard regression suite."""
from datetime import datetime, timezone
from pathlib import Path
import csv
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import ch065_retention_review as r

NOW=datetime(2026,11,1,tzinfo=timezone.utc)

def eligible():
    return {
        "backup_id":"SYNTHETIC-001","backup_type":"physical",
        "start_utc":"2026-09-01T00:00:00Z",
        "end_utc":"2026-09-01T00:15:00Z",
        "timeline":"00000001",
        "wal_start":"SYNTHETIC-WAL-START",
        "wal_end":"SYNTHETIC-WAL-END",
        "manifest_verified":"yes","offsite_copy_verified":"yes",
        "immutable_until_utc":"","legal_hold":"no",
        "retention_class":"synthetic-test",
        "expiry_candidate_utc":"2026-10-01T00:00:00Z",
        "dependency_chain_verified":"yes","restore_tested":"yes",
        "decision":"PENDING_REVIEW","reviewer":"synthetic-independent-reviewer",
        "notes":"No real deletion, even if metadata is complete"
    }

def examine(row):
    return r.screen([row],NOW,list(r.REQUIRED))


class RetentionRefusal(unittest.TestCase):
    def test_fully_synthetic_still_not_authorized(self):
        s=examine(eligible())
        self.assertEqual("METADATA_REVIEW_POSSIBLE_UNAUTHENTICATED",s["decision"])
        self.assertEqual(1,s["eligible_for_review"])
        self.assertFalse(s["deletion_authorized"])
        self.assertFalse(s["source_provenance_authenticated"])

    def test_all_unverified_dependencies_refused(self):
        for field in ("manifest_verified","offsite_copy_verified",
                      "dependency_chain_verified","restore_tested"):
            for value in ("no", "", "unknown"):
                with self.subTest(field=field,value=value):
                    row=eligible()
                    row[field]=value
                    self.assertEqual("NO_GO",examine(row)["decision"])

    def test_legal_hold_and_immutability_refused(self):
        for key,value in (("legal_hold","yes"),("legal_hold","unknown"),
                          ("immutable_until_utc","2026-12-01T00:00:00Z"),
                          ("immutable_until_utc","invalid")):
            with self.subTest(key=key,value=value):
                row=eligible();row[key]=value
                self.assertEqual("NO_GO",examine(row)["decision"])

    def test_expiry_and_backup_window_fail_closed(self):
        for key,value in (("expiry_candidate_utc","2026-12-01T00:00:00Z"),
                          ("expiry_candidate_utc",""),
                          ("start_utc","2026-09-02T00:00:00Z"),
                          ("end_utc","2026-08-30T00:00:00Z"),
                          ("start_utc","2026-09-01T00:00:00"),
                          ("end_utc","2026-11-02T00:00:00Z")):
            with self.subTest(key=key,value=value):
                row=eligible();row[key]=value
                self.assertEqual("NO_GO",examine(row)["decision"])

    def test_unsupported_backup_and_unsafe_disposition(self):
        for field,value in (("backup_type","physical_and_logical"),("decision","DELETE")):
            row=eligible();row[field]=value
            self.assertEqual("NO_GO",examine(row)["decision"])

    def test_missing_id_duplicate_id_or_empty_packet(self):
        self.assertEqual("NO_GO",r.screen([],NOW,list(r.REQUIRED))["decision"])
        row=eligible()
        self.assertEqual("NO_GO",r.screen([row,row],NOW,list(r.REQUIRED))["decision"])
        row["backup_id"]=""
        self.assertEqual("NO_GO",examine(row)["decision"])

    def test_missing_required_columns(self):
        self.assertEqual("NO_GO",r.screen([eligible()],NOW,["backup_id"])["decision"])

    def test_public_template_remains_no_go(self):
        f=Path(__file__).resolve().parents[1]/"labs"/"retention"/"065-retention-decision-template.csv"
        with f.open(encoding="utf-8",newline="") as file:
            rd=csv.DictReader(file)
            result=r.screen(list(rd),NOW,rd.fieldnames)
        self.assertEqual("NO_GO",result["decision"])
        self.assertFalse(result["deletion_authorized"])

    def test_cli_never_deletes_or_accepts_ambiguous_clock(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"synthetic.csv"
            with p.open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=sorted(r.REQUIRED))
                w.writeheader(); w.writerow(eligible())
            cmd=[sys.executable,str(Path(r.__file__)),"--csv",str(p)]
            out=subprocess.run(cmd+["--now-utc","2026-11-01T00:00:00"],
                               capture_output=True,text=True)
            self.assertEqual(2,out.returncode)
            good=subprocess.run(cmd+["--now-utc","2026-11-01T00:00:00Z"],
                                capture_output=True,text=True)
            self.assertEqual(0,good.returncode,good.stderr)
            self.assertIn('"deletion_authorized": false',good.stdout)
            self.assertTrue(p.exists())


if __name__=="__main__":
    unittest.main()
